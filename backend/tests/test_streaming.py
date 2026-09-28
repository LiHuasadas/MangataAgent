"""Verify the POST SSE endpoint forwards live progress and terminal events."""

import asyncio
import json
from types import SimpleNamespace

from backend.app.api import conversations
from backend.app.agents.host_agent import HostAgent
from backend.app.chat.repository import RedisConversationRepository
from backend.app.core.message import ChatMessage


class ConnectedRequest:
    async def is_disconnected(self):
        return False


def test_stream_forwards_progress_delta_and_answer(monkeypatch):
    async def fake_send(**kwargs):
        await kwargs["progress_callback"]({"type": "progress", "stage": "routing", "message": "正在分析请求"})
        await kwargs["progress_callback"]({"type": "delta", "content": "回答"})
        return SimpleNamespace(model_dump=lambda **options: {"answer": "回答", "status": "completed"})

    monkeypatch.setattr(conversations, "_send_message", fake_send)

    async def run():
        response = await conversations.send_message_stream(
            conversation_id="c1", body=object(), request=ConnectedRequest(),
            user_id="alice", service=object(), agent=object(),
        )
        return [chunk async for chunk in response.body_iterator]

    frames = asyncio.run(run())
    events = [json.loads(frame.removeprefix("data: ").strip()) for frame in frames[:-1]]
    assert [event["type"] for event in events] == ["ack", "progress", "delta", "answer"]
    assert events[-1]["data"]["answer"] == "回答"
    assert frames[-1] == "data: [DONE]\n\n"


def test_stream_reports_turn_failure_and_finishes(monkeypatch):
    async def fake_send(**kwargs):
        raise ValueError("agent offline")

    monkeypatch.setattr(conversations, "_send_message", fake_send)

    async def run():
        response = await conversations.send_message_stream(
            conversation_id="c1", body=object(), request=ConnectedRequest(),
            user_id="alice", service=object(), agent=object(),
        )
        return [chunk async for chunk in response.body_iterator]

    frames = asyncio.run(run())
    assert json.loads(frames[1].removeprefix("data: ")) == {
        "type": "error", "detail": "agent offline"
    }
    assert frames[-1] == "data: [DONE]\n\n"


def test_host_consolidation_emits_real_model_chunks():
    class StreamingLLM:
        def stream_invoke(self, messages):
            yield "第一段"
            yield "第二段"

    host = HostAgent.__new__(HostAgent)
    host.llm = StreamingLLM()
    events = []

    async def publish(event):
        events.append(event)

    result = asyncio.run(host._consolidate_results(
        "问题", [{"agent_type": "simple_agent", "success": True,
                 "response": "事实", "artifacts": []}], progress_callback=publish
    ))
    assert result["response"] == "第一段第二段"
    assert events == [
        {"type": "delta", "content": "第一段"},
        {"type": "delta", "content": "第二段"},
    ]


def test_recent_history_returns_latest_messages_in_chat_order():
    messages = {
        str(sequence): ChatMessage(
            message_id=str(sequence), conversation_id="c1", user_id="alice",
            request_id=str(sequence), role="user", content=str(sequence), sequence=sequence,
        ).model_dump_json()
        for sequence in (2, 3)
    }
    repository = RedisConversationRepository.__new__(RedisConversationRepository)
    repository.get_conversation = lambda user_id, conversation_id: None
    repository._keys = lambda user_id, conversation_id: ("conversation", "messages", "order", "turn")
    repository.redis = SimpleNamespace(
        zrevrange=lambda key, start, end: ["3", "2"],
        hmget=lambda key, ids: [messages[item] for item in ids],
    )

    result = repository.list_recent_messages("alice", "c1", limit=2)
    assert [message.sequence for message in result] == [2, 3]
