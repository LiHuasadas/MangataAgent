"""Conversation and messaging endpoints for frontend."""

import asyncio
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
import json
from typing import Awaitable, Callable, Optional

from ..chat.models import TurnStatus
from ..chat.service import ChatService
from ..agents.host_agent import HostAgent
from ..protocols.types import Task, TaskState, TaskStatus, TaskTenantContext, Message as A2AMessage, TextPart
from .dependencies import get_current_user_id, get_chat_service, get_host_agent
from .schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    MessageItemResponse,
    MessageListResponse,
    SendMessageRequest,
    TurnResponse,
)

router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreateRequest = None,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    """Create a new conversation for the authenticated user."""
    conv = service.create_conversation(user_id)
    return ConversationResponse(
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    """List conversations for the current user."""
    items = service.list_conversations(user_id, offset=offset, limit=limit)
    return ConversationListResponse(
        items=[
            ConversationResponse(
                conversation_id=c.conversation_id,
                user_id=c.user_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
        offset=offset,
        limit=limit,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    """Get metadata for a specific conversation."""
    conv = service.get_conversation(user_id, conversation_id)
    return ConversationResponse(
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: str,
    after_sequence: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    """List messages in a conversation ordered chronologically."""
    messages = service.list_messages(user_id, conversation_id, after_sequence=after_sequence, limit=limit)
    return MessageListResponse(
        items=[
            MessageItemResponse(
                message_id=m.message_id,
                conversation_id=m.conversation_id,
                user_id=m.user_id,
                request_id=m.request_id,
                role=m.role,
                content=m.content,
                sequence=m.sequence,
                created_at=m.created_at,
                reply_to_message_id=m.reply_to_message_id,
                metadata=m.metadata,
            )
            for m in messages
        ],
        after_sequence=after_sequence,
        limit=limit,
    )


@router.get("/{conversation_id}/turns/{request_id}", response_model=TurnResponse)
def get_turn(
    conversation_id: str,
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    """Get the status of a specific turn execution."""
    turn = service.get_turn(user_id, conversation_id, request_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")

    answer = None
    if turn.assistant_message_id:
        try:
            msg = service.get_message(user_id, conversation_id, turn.assistant_message_id)
            answer = msg.content
        except Exception:
            pass

    return TurnResponse(
        conversation_id=turn.conversation_id,
        request_id=turn.request_id,
        status=turn.status.value,
        user_message_id=turn.user_message_id,
        assistant_message_id=turn.assistant_message_id,
        answer=answer,
        error=turn.error,
    )


async def _send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
    agent: HostAgent = Depends(get_host_agent),
    progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
):
    """Send a message to the HostAgent and receive response with multi-agent coordination."""
    request_id = body.request_id or str(uuid4())

    # 1. Begin turn (Redis distributed lock & idempotency check)
    turn = service.begin_turn(user_id, conversation_id, request_id, body.content)

    # If turn is already completed, return cached response
    if turn.status == TurnStatus.COMPLETED:
        answer = None
        if turn.assistant_message_id:
            try:
                msg = service.get_message(user_id, conversation_id, turn.assistant_message_id)
                answer = msg.content
            except Exception:
                pass
        return TurnResponse(
            conversation_id=conversation_id,
            request_id=request_id,
            status=turn.status.value,
            user_message_id=turn.user_message_id,
            assistant_message_id=turn.assistant_message_id,
            answer=answer,
        )

    if not turn.lock_token:
        return TurnResponse(
            conversation_id=conversation_id,
            request_id=request_id,
            status=turn.status.value,
            user_message_id=turn.user_message_id,
            assistant_message_id=turn.assistant_message_id,
            error=turn.error,
        )

    lock_token = turn.lock_token
    stop_renew = asyncio.Event()

    # Background lease renewer
    async def renew_worker():
        while not stop_renew.is_set():
            try:
                await asyncio.sleep(5)
                if stop_renew.is_set():
                    break
                service.renew_turn(user_id, conversation_id, request_id, lock_token)
            except Exception:
                break

    renew_task = asyncio.create_task(renew_worker())

    try:
        # 2. Inject conversation history into HostAgent
        history_msgs = service.list_recent_messages(user_id, conversation_id, limit=50)
        history = [
            m.to_llm_message() for m in history_msgs
            if m.role in ("user", "assistant") and m.message_id != turn.user_message_id
        ]

        # 3. Build Task and TenantContext (default to user_id + conversation_id)
        effective_workspace = (
            body.workspace_id.strip()
            if (body.workspace_id and body.workspace_id.strip() and body.workspace_id.strip() != "default")
            else f"{user_id}_{conversation_id}"
        )
        context = TaskTenantContext(
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            workspace_id=effective_workspace,
        )
        task = Task(
            id=str(uuid4()),
            tenant_context=context,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                message=A2AMessage(parts=[TextPart(text=body.content)]),
            ),
        )

        # 4. Execute HostAgent orchestration
        result_task = await agent.handle_task(
            task, conversation_history=history, progress_callback=progress_callback
        )

        # 5. Extract answer text
        answer_parts = []
        if result_task.status.message and result_task.status.message.parts:
            for part in result_task.status.message.parts:
                if hasattr(part, "text") and part.text:
                    answer_parts.append(part.text)
        answer = "\n\n".join(answer_parts) if answer_parts else "处理完成，无文字输出"

        # 6. Complete turn in Redis
        completed = service.complete_turn(user_id, conversation_id, request_id, lock_token, answer)
        agent_results = result_task.metadata.get("agent_results", [])
        artifacts = [a.model_dump() if hasattr(a, "model_dump") else dict(a) for a in result_task.artifacts]

        return TurnResponse(
            conversation_id=conversation_id,
            request_id=request_id,
            status=completed.status.value,
            user_message_id=completed.user_message_id,
            assistant_message_id=completed.assistant_message_id,
            answer=answer,
            agent_results=agent_results,
            artifacts=artifacts,
        )

    except Exception as exc:
        try:
            service.fail_turn(user_id, conversation_id, request_id, lock_token, str(exc))
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"智能体执行异常: {str(exc)}",
        )
    finally:
        stop_renew.set()
        renew_task.cancel()


@router.post("/{conversation_id}/messages", response_model=TurnResponse)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
    agent: HostAgent = Depends(get_host_agent),
):
    return await _send_message(conversation_id, body, user_id, service, agent)


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    body: SendMessageRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
    agent: HostAgent = Depends(get_host_agent),
):
    """Stream HostAgent progress and answer chunks over a POST SSE response."""
    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        connected = True

        async def publish(event: dict):
            if connected:
                await queue.put(event)

        async def run_turn():
            try:
                response = await _send_message(
                    conversation_id=conversation_id,
                    body=body,
                    user_id=user_id,
                    service=service,
                    agent=agent,
                    progress_callback=publish,
                )
                await publish({"type": "answer", "data": response.model_dump(mode="json")})
            except Exception as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                await publish({"type": "error", "detail": detail})
            finally:
                await publish({"type": "done"})

        worker = asyncio.create_task(run_turn())
        try:
            yield f"data: {json.dumps({'type': 'ack', 'conversation_id': conversation_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event["type"] == "done":
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            connected = False

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
