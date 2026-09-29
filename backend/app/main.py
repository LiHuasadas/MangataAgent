"""MangataAgent 服务入口：每次只启动一个 Agent。"""

import argparse
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / "backend" / ".env")

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from redis import Redis

from backend.app.api import api_router
from backend.app.chat.config import ChatRedisConfig
from backend.app.chat.models import (
    ConversationBusy, ConversationNotFound, LeaseLost, MessageNotFound,
    RequestConflict, TurnStateConflict,
)
from backend.app.chat.repository import RedisConversationRepository
from backend.app.chat.service import ChatService
from backend.app.core.llm import HelloAgentsLLM
from backend.app.agents.host_agent import HostAgent


DEFAULT_PORTS = {
    "host": 8000,
    "plan_solve": 8001,
    "react": 8002,
    "reflection": 8003,
    "simple": 8004,
}


def create_llm() -> HelloAgentsLLM:
    return HelloAgentsLLM(
        provider="custom",
        model=os.getenv("LLM_MODEL_ID", "qwen-plus"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
    )


def agent_options(host: str, port: int) -> dict:
    workspace = PROJECT_ROOT / "project"
    kb_path = PROJECT_ROOT / "kb"
    workspace.mkdir(parents=True, exist_ok=True)
    kb_path.mkdir(parents=True, exist_ok=True)
    return dict(
        llm=create_llm(),
        user_id="system",
        knowledge_base_path=str(kb_path),
        rag_namespace="reports",
        workspace=str(workspace),
        host=host,
        port=port,
    )


def create_host_agent() -> HostAgent:
    """供 API 网关在启动时创建编排 Agent。"""
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "8000"))
    return HostAgent(
        name="HostAgent",
        **agent_options(host, port),
        plan_solve_agent_url=os.getenv("PLAN_SOLVE_AGENT_URL", "http://localhost:8001"),
        react_agent_url=os.getenv("REACT_AGENT_URL", "http://localhost:8002"),
        reflection_agent_url=os.getenv("REFLECTION_AGENT_URL", "http://localhost:8003"),
        simple_agent_url=os.getenv("SIMPLE_AGENT_URL", "http://localhost:8004"),
    )


def create_specialist(name: str, host: str, port: int):
    """按需导入并创建一个专长 Agent。"""
    if name == "plan_solve":
        from backend.app.agents.plan_solve_agent import PlanAndSolveAgent
        agent_class = PlanAndSolveAgent
    elif name == "react":
        from backend.app.agents.react_agent import ContextAwareAgent
        agent_class = ContextAwareAgent
    elif name == "reflection":
        from backend.app.agents.reflection_agent import ReflectionAgent
        agent_class = ReflectionAgent
    elif name == "simple":
        from backend.app.agents.simple_agent import SimpleAgent
        agent_class = SimpleAgent
    else:
        raise ValueError(f"未知 Agent: {name}")
    return agent_class(name=f"{name}_agent", **agent_options(host, port))


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_config = ChatRedisConfig.from_env()
    redis_client = Redis.from_url(redis_config.url, decode_responses=True)
    host_agent = None
    try:
        redis_client.ping()
        repository = RedisConversationRepository(redis_client, redis_config)
        host_agent = create_host_agent()
        await host_agent.startup()

        from backend.app.core.auth_service import AuthService
        from backend.app.core.workspace_service import WorkspaceService

        app.state.redis = redis_client
        app.state.chat_service = ChatService(repository)
        app.state.host_agent = host_agent
        app.state.workspace_service = WorkspaceService(base_dir=PROJECT_ROOT / "project")
        app.state.auth_service = AuthService(redis_client)
        yield
    finally:
        try:
            if host_agent is not None:
                await host_agent.client.close()
        finally:
            redis_client.close()


app = FastAPI(title="MangataAgent API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConversationNotFound)
async def conversation_not_found_handler(request: Request, exc: ConversationNotFound):
    return JSONResponse(status_code=404, content={"detail": f"会话不存在: {exc}"})


@app.exception_handler(MessageNotFound)
async def message_not_found_handler(request: Request, exc: MessageNotFound):
    return JSONResponse(status_code=404, content={"detail": f"消息不存在: {exc}"})


@app.exception_handler(ConversationBusy)
async def conversation_busy_handler(request: Request, exc: ConversationBusy):
    return JSONResponse(status_code=409, content={"detail": f"会话正在处理上一轮请求，请稍候: {exc}"})


@app.exception_handler(LeaseLost)
async def lease_lost_handler(request: Request, exc: LeaseLost):
    return JSONResponse(status_code=409, content={"detail": f"锁租约已丢失或超时: {exc}"})


@app.exception_handler(RequestConflict)
async def request_conflict_handler(request: Request, exc: RequestConflict):
    return JSONResponse(status_code=409, content={"detail": f"请求冲突或请求ID重复: {exc}"})


@app.exception_handler(TurnStateConflict)
async def turn_conflict_handler(request: Request, exc: TurnStateConflict):
    return JSONResponse(status_code=409, content={"detail": f"轮次状态冲突: {exc}"})


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(api_router, prefix="/api/v1")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="分别启动 MangataAgent 服务")
    parser.add_argument("--agent", choices=DEFAULT_PORTS, default="host")
    parser.add_argument("--host", default=os.getenv("A2A_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    port = args.port if args.port is not None else DEFAULT_PORTS[args.agent]
    if args.model:
        os.environ["LLM_MODEL_ID"] = args.model
    if args.base_url:
        os.environ["LLM_BASE_URL"] = args.base_url

    print(f"Starting {args.agent} on {args.host}:{port}")
    if args.agent == "host":
        os.environ["A2A_HOST"] = args.host
        os.environ["A2A_PORT"] = str(port)
        uvicorn.run(app, host=args.host, port=port)
    else:
        agent = create_specialist(args.agent, args.host, port)
        uvicorn.run(agent.app, host=args.host, port=port)


if __name__ == "__main__":
    main()
