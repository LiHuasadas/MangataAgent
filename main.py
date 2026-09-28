"""
MangataAgent 多智能体系统主入口。
支持分别启动单个 Agent 或一键启动全部 Agent 与前端 Web UI。
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

# 确保 Windows 终端 UTF-8 编码，防止特殊字符或 emoji 引发 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

# 统一默认 A2A Token
if not os.getenv("A2A_SERVICE_TOKEN"):
    os.environ["A2A_SERVICE_TOKEN"] = "mangata-secret-token-2026"

DEFAULT_PORTS = {
    "host": 8000,
    "plan_solve": 8001,
    "plan_solve_agent": 8001,
    "react": 8002,
    "react_agent": 8002,
    "reflection": 8003,
    "reflection_agent": 8003,
    "simple": 8004,
    "simple_agent": 8004,
}


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="MangataAgent 多智能体系统")
    parser.add_argument(
        "--agent",
        choices=[
            "all",
            "host",
            "plan_solve", "plan_solve_agent",
            "react", "react_agent",
            "reflection", "reflection_agent",
            "simple", "simple_agent"
        ],
        default="all",
        help="要启动的智能体（默认：all 一键启动全部）"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("A2A_HOST", "127.0.0.1"),
        help="绑定的主机地址（默认：127.0.0.1）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="绑定的端口（默认根据 agent 自动分配：host=8000, plan_solve=8001, react=8002, reflection=8003, simple=8004）"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="使用的模型（默认读取 .env 中的 LLM_MODEL_ID）"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="LLM API 的基础地址（默认读取 .env 中的 LLM_BASE_URL）"
    )
    parser.add_argument(
        "--with-ui",
        action="store_true",
        help="启动所有 Agent 时是否同时启动前端 Web UI"
    )
    return parser.parse_args()


def run_specialist(agent_name: str, host: str, port: int, model: str | None = None, base_url: str | None = None):
    """启动专长智能体。"""
    from backend.app.agents.serve import create_specialist
    import uvicorn

    agent, bound_port = create_specialist(
        agent_type=agent_name,
        port=port,
        host=host,
        model=model,
        base_url=base_url,
    )
    print(f"🚀 [{agent.name}] 正在启动 -> http://{host}:{bound_port}")
    uvicorn.run(agent.app, host=host, port=bound_port)


def run_host(host: str, port: int, model: str | None = None, base_url: str | None = None):
    """启动主机编排智能体与 API 网关。"""
    import uvicorn

    # 当独立启动 host 时，默认不自动在内部派生子进程，便于连接独立终端启动的专长智能体
    os.environ.setdefault("AUTO_START_SPECIALISTS", "false")
    os.environ["A2A_HOST"] = host
    os.environ["A2A_PORT"] = str(port)

    if model:
        os.environ["LLM_MODEL_ID"] = model
    if base_url:
        os.environ["LLM_BASE_URL"] = base_url

    print(f"🚀 [HostAgent] 正在启动主网关 -> http://{host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port)


def run_all(host: str, model: str | None = None, base_url: str | None = None, with_ui: bool = False):
    """一键以多进程启动所有智能体服务。"""
    print("=" * 65)
    print("🌟 正在一键启动 MangataAgent 全套多智能体集群...")
    print("=" * 65)

    specialists = [
        ("plan_solve", 8001, "Plan & Solve Agent (架构规划与侦察)"),
        ("react", 8002, "ReAct Agent (主力编码与工具执行)"),
        ("reflection", 8003, "Reflection Agent (代码审查与测试质检)"),
        ("simple", 8004, "Simple Agent (轻量快速直答)"),
    ]

    processes = []
    child_env = os.environ.copy()
    child_env["PYTHONUNBUFFERED"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["A2A_SERVICE_TOKEN"] = os.getenv("A2A_SERVICE_TOKEN", "mangata-secret-token-2026")
    if model:
        child_env["LLM_MODEL_ID"] = model
    if base_url:
        child_env["LLM_BASE_URL"] = base_url

    try:
        # 1. 启动 4 个专长子智能体
        for name, port, desc in specialists:
            cmd = [
                sys.executable, str(PROJECT_ROOT / "main.py"),
                "--agent", name,
                "--host", host,
                "--port", str(port),
            ]
            if model:
                cmd.extend(["--model", model])
            if base_url:
                cmd.extend(["--base-url", base_url])

            p = subprocess.Popen(cmd, env=child_env)
            processes.append((name, p))
            print(f"  [+] 启动专长智能体: {desc} (端口 {port})")

        # 2. 给予子智能体初始化时间
        print("\n⏳ 正在等待各专长智能体初始化完成...")
        time.sleep(3)

        # 3. 启动 Host Agent / 网关 (端口 8000)
        host_env = child_env.copy()
        host_env["AUTO_START_SPECIALISTS"] = "false"
        host_cmd = [
            sys.executable, str(PROJECT_ROOT / "main.py"),
            "--agent", "host",
            "--host", host,
            "--port", "8000",
        ]
        if model:
            host_cmd.extend(["--model", model])
        if base_url:
            host_cmd.extend(["--base-url", base_url])

        host_p = subprocess.Popen(host_cmd, env=host_env)
        processes.append(("host", host_p))
        print("  [+] 启动主机编排网关: HostAgent (端口 8000)")

        # 4. 可选启动前端 UI
        if with_ui:
            ui_cmd = [sys.executable, str(PROJECT_ROOT / "run_ui.py")]
            ui_p = subprocess.Popen(ui_cmd, env=child_env)
            processes.append(("web_ui", ui_p))
            print("  [+] 启动前端 Web UI -> http://localhost:5173")

        print("\n" + "=" * 65)
        print("✅ MangataAgent 多智能体集群全部就绪！")
        print(f"📖 Host API 接口文档: http://{host}:8000/docs")
        print(f"🔍 Plan & Solve Agent: http://{host}:8001/.well-known/agent.json")
        print(f"⚡ ReAct Agent:        http://{host}:8002/.well-known/agent.json")
        print(f"🛡️ Reflection Agent:   http://{host}:8003/.well-known/agent.json")
        print(f"💬 Simple Agent:       http://{host}:8004/.well-known/agent.json")
        if with_ui:
            print("🌐 Web UI 界面:        http://localhost:5173")
        print("\n💡 提示: 按 Ctrl+C 可一键停止所有智能体服务。")
        print("=" * 65 + "\n")

        # 监控所有进程
        for _, p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\n🛑 收到终止信号，正在关闭所有智能体进程...")
        for name, p in processes:
            if p.poll() is None:
                p.terminate()
        for name, p in processes:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("✅ 所有智能体服务已安全退出。")


def main():
    args = parse_args()
    port = args.port or DEFAULT_PORTS.get(args.agent, 8000)

    if args.agent == "all":
        run_all(
            host=args.host,
            model=args.model,
            base_url=args.base_url,
            with_ui=args.with_ui,
        )
    elif args.agent in ("host", "host_agent"):
        run_host(
            host=args.host,
            port=port,
            model=args.model,
            base_url=args.base_url,
        )
    else:
        run_specialist(
            agent_name=args.agent,
            host=args.host,
            port=port,
            model=args.model,
            base_url=args.base_url,
        )


if __name__ == "__main__":
    main()
