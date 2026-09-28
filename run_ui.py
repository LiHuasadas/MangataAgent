"""
启动 MangataAgent 前端 Web UI (Vite + React)。
"""
import argparse
from pathlib import Path
import subprocess
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def parse_args():
    parser = argparse.ArgumentParser(description="MangataAgent 前端 Web UI")
    parser.add_argument(
        "--port",
        type=int,
        default=5173,
        help="前端监听端口（默认：5173）"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="前端监听主机（默认：localhost）"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"🚀 正在启动 MangataAgent 前端 Web UI: http://{args.host}:{args.port}")

    # 使用 npx vite 保证端口与主机参数直接生效
    cmd = ["npx", "vite", "--port", str(args.port), "--host", args.host]
    if sys.platform == "win32":
        cmd = ["cmd", "/c"] + cmd

    try:
        subprocess.run(cmd, cwd=FRONTEND_DIR, check=True)
    except KeyboardInterrupt:
        print("\nWeb UI 已停止。")
    except Exception as e:
        print(f"\n❌ 启动前端失败: {e}")


if __name__ == "__main__":
    main()
