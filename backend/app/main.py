"""FastAPI Application Entry Point for MangataAgent."""

import os
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

import uvicorn
from fastapi import FastAPI, Request, status
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
from backend.app.agents.local_services import start_local_specialists, stop_local_specialists


def create_host_agent() -> HostAgent:
    """Initialize HostAgent with system configs."""
    workspace = PROJECT_ROOT / "project"
    workspace.mkdir(parents=True, exist_ok=True)
    kb_path = PROJECT_ROOT / "kb"
    kb_path.mkdir(parents=True, exist_ok=True)

    llm = HelloAgentsLLM(
        provider="custom",
        model=os.getenv("LLM_MODEL_ID", "qwen-plus"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
    )

    host_agent = HostAgent(
        name="HostAgent",
        llm=llm,
        user_id="system",
        knowledge_base_path=str(kb_path),
        rag_namespace="reports",
        workspace=str(workspace),
        host=os.getenv("A2A_HOST", "localhost"),
        port=int(os.getenv("A2A_PORT", "8000")),
        plan_solve_agent_url=os.getenv("PLAN_SOLVE_AGENT_URL", "http://localhost:8001"),
        react_agent_url=os.getenv("REACT_AGENT_URL", "http://localhost:8002"),
        reflection_agent_url=os.getenv("REFLECTION_AGENT_URL", "http://localhost:8003"),
        simple_agent_url=os.getenv("SIMPLE_AGENT_URL", "http://localhost:8004"),
    )
    return host_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_config = ChatRedisConfig.from_env()
    redis_client = Redis.from_url(redis_config.url, decode_responses=True)
    host_agent = None
    specialist_processes = {}
    try:
        try:
            redis_client.ping()
        except Exception as exc:
            print(f"⚠️ Redis 连接异常: {exc}，请确保 Redis 正在运行。")
            raise
        print(f"✅ Redis 已成功连接: {redis_config.url}")
        repository = RedisConversationRepository(redis_client, redis_config)
        chat_service = ChatService(repository)

        auto_start = os.getenv("AUTO_START_SPECIALISTS", "false").lower() in {"1", "true", "yes"}
        generated_token = False
        if auto_start and not os.getenv("A2A_SERVICE_TOKEN"):
            os.environ["A2A_SERVICE_TOKEN"] = secrets.token_urlsafe(32)
            generated_token = True
            print("🔐 已为本次本地启动生成 A2A 服务令牌")

        print("🚀 正在初始化 HostAgent 与编排引擎...")
        host_agent = create_host_agent()
        if auto_start:
            specialist_processes = await start_local_specialists(
                host_agent, PROJECT_ROOT, reuse_existing=not generated_token
            )
        else:
            await host_agent.startup()

        from backend.app.core.workspace_service import WorkspaceService
        from backend.app.core.auth_service import AuthService
        app.state.redis = redis_client
        app.state.chat_service = chat_service
        app.state.host_agent = host_agent
        app.state.workspace_service = WorkspaceService(base_dir=PROJECT_ROOT / "project")
        app.state.auth_service = AuthService(redis_client)

        print("🌟 MangataAgent FastAPI 服务就绪！")
        print(f"📖 API 接口文档: http://127.0.0.1:{os.getenv('A2A_PORT', '8000')}/docs")
        yield
    finally:
        print("🛑 正在停止服务并释放资源...")
        try:
            await stop_local_specialists(specialist_processes)
        finally:
            try:
                if host_agent is not None:
                    await host_agent.client.close()
            finally:
                redis_client.close()


app = FastAPI(
    title="MangataAgent API",
    description="面向前端交互的 Mangata 多智能体协同管理平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 跨域配置（允许前端 Web/Vite/Next.js 等应用无缝调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一异常映射处理
@app.exception_handler(ConversationNotFound)
async def conversation_not_found_handler(request: Request, exc: ConversationNotFound):
    return JSONResponse(status_code=404, content={"detail": f"会话不存在: {str(exc)}"})

@app.exception_handler(MessageNotFound)
async def message_not_found_handler(request: Request, exc: MessageNotFound):
    return JSONResponse(status_code=404, content={"detail": f"消息不存在: {str(exc)}"})

@app.exception_handler(ConversationBusy)
async def conversation_busy_handler(request: Request, exc: ConversationBusy):
    return JSONResponse(status_code=409, content={"detail": f"会话正在处理上一轮请求，请稍候: {str(exc)}"})

@app.exception_handler(LeaseLost)
async def lease_lost_handler(request: Request, exc: LeaseLost):
    return JSONResponse(status_code=409, content={"detail": f"锁租约已丢失或超时: {str(exc)}"})

@app.exception_handler(RequestConflict)
async def request_conflict_handler(request: Request, exc: RequestConflict):
    return JSONResponse(status_code=409, content={"detail": f"请求冲突或请求ID重复: {str(exc)}"})

@app.exception_handler(TurnStateConflict)
async def turn_conflict_handler(request: Request, exc: TurnStateConflict):
    return JSONResponse(status_code=409, content={"detail": f"轮次状态冲突: {str(exc)}"})

# 根路径重定向到 Swagger 文档
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    os.environ.setdefault("AUTO_START_SPECIALISTS", "true")
    uvicorn.run("backend.app.main:app", host=os.getenv("A2A_HOST", "0.0.0.0"),
                port=int(os.getenv("A2A_PORT", "8000")), reload=True)
