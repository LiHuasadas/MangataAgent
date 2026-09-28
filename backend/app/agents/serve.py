"""Run one specialist A2A service: python -m backend.app.agents.serve simple."""

import argparse
from importlib import import_module
import os
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[3]
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

SPECIALISTS_MAP = {
    "plan_solve": ("plan_solve_agent", "PlanAndSolveAgent", 8001),
    "plan_solve_agent": ("plan_solve_agent", "PlanAndSolveAgent", 8001),
    "react": ("react_agent", "ContextAwareAgent", 8002),
    "react_agent": ("react_agent", "ContextAwareAgent", 8002),
    "reflection": ("reflection_agent", "ReflectionAgent", 8003),
    "reflection_agent": ("reflection_agent", "ReflectionAgent", 8003),
    "simple": ("simple_agent", "SimpleAgent", 8004),
    "simple_agent": ("simple_agent", "SimpleAgent", 8004),
}


def create_specialist(
    agent_type: str,
    port: int | None = None,
    host: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
):
    # Ensure standard token is present so A2A auth succeeds out of the box
    if not os.getenv("A2A_SERVICE_TOKEN"):
        os.environ["A2A_SERVICE_TOKEN"] = "mangata-secret-token-2026"

    from backend.app.core.llm import HelloAgentsLLM

    if agent_type not in SPECIALISTS_MAP:
        raise ValueError(f"Unknown agent type: {agent_type}. Choices: {list(SPECIALISTS_MAP.keys())}")

    module_name, class_name, default_port = SPECIALISTS_MAP[agent_type]
    agent_class = getattr(import_module(f"backend.app.agents.{module_name}"), class_name)
    port = port or default_port
    host = host or os.getenv("A2A_HOST", "127.0.0.1")

    llm = HelloAgentsLLM(
        provider="custom",
        model=model or os.getenv("LLM_MODEL_ID", "qwen-plus"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
    )
    workspace = PROJECT_ROOT / "project"
    knowledge_base = PROJECT_ROOT / "kb"
    workspace.mkdir(parents=True, exist_ok=True)
    knowledge_base.mkdir(parents=True, exist_ok=True)

    agent = agent_class(
        name=agent_type if agent_type.endswith("_agent") else f"{agent_type}_agent",
        llm=llm,
        user_id="system",
        knowledge_base_path=str(knowledge_base),
        rag_namespace="reports",
        workspace=str(workspace),
        host=host,
        port=port,
    )
    return agent, port


def main():
    parser = argparse.ArgumentParser(description="Run one MangataAgent specialist A2A service")
    parser.add_argument("agent_type", choices=list(SPECIALISTS_MAP.keys()), help="Agent type to run")
    parser.add_argument("--host", default=os.getenv("A2A_HOST", "127.0.0.1"), help="Host to bind")
    parser.add_argument("--port", type=int, help="Port to bind (defaults to this specialist's standard port)")
    parser.add_argument("--model", help="LLM model name")
    parser.add_argument("--base-url", help="LLM base URL")
    args = parser.parse_args()

    agent, port = create_specialist(
        args.agent_type,
        port=args.port,
        host=args.host,
        model=args.model,
        base_url=args.base_url,
    )

    import uvicorn
    uvicorn.run(agent.app, host=args.host, port=port)


if __name__ == "__main__":
    main()

