"""Manage local specialist processes owned by the FastAPI gateway."""

import asyncio
from collections import deque
import os
import subprocess
import sys
import threading
from urllib.parse import urlsplit


def local_port(url: str) -> int | None:
    """Return a local HTTP service port, or None for an external A2A URL."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                and parsed.path in {"", "/"} and parsed.port):
            return parsed.port
    except ValueError:
        pass
    return None


async def stop_local_specialists(processes: dict) -> None:
    """Stop only the child processes created by this gateway worker."""
    children = list(processes.values())
    for process in children:
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    async def wait_for_exit(process):
        try:
            await asyncio.to_thread(process.wait, timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await asyncio.to_thread(process.wait)

    await asyncio.gather(*(wait_for_exit(process) for process in children))


async def start_local_specialists(host_agent, project_root, *, reuse_existing: bool = True) -> dict:
    """Start missing local specialists and wait for every configured A2A card."""
    processes = {}
    log_threads = {}
    recent_logs = {}

    async def discover(name: str, url: str):
        try:
            card = await asyncio.wait_for(host_agent.client.discover_agent(url), timeout=2)
        except (Exception, asyncio.TimeoutError):
            return False
        host_agent.agent_capabilities[name] = card
        return True

    def forward_logs(name: str, process):
        if process.stdout is None:
            return
        for line in process.stdout:
            message = line.rstrip("\r\n")
            recent_logs[name].append(message)
            print(f"[{name}] {message}", flush=True)
        process.stdout.close()

    async def failure_detail(name: str) -> str:
        thread = log_threads.get(name)
        if thread is not None:
            await asyncio.to_thread(thread.join, 1)
        lines = recent_logs.get(name)
        return "\n" + "\n".join(f"[{name}] {line}" for line in lines) if lines else ""

    try:
        timeout = max(1, int(os.getenv("SPECIALIST_STARTUP_TIMEOUT", "120")))
        for name, url in host_agent.agent_urls.items():
            if await discover(name, url):
                if not reuse_existing:
                    raise RuntimeError(
                        f"{name} 已在 {url} 运行，但网关使用本次新生成的 A2A 令牌；"
                        "请为所有进程配置相同的 A2A_SERVICE_TOKEN，或停止现有服务"
                    )
                print(f"✅ 已连接现有 {name}: {url}")
                continue

            port = local_port(url)
            if port is None:
                if not reuse_existing:
                    raise RuntimeError(f"外部子智能体 {name} 需要预先配置共享的 A2A_SERVICE_TOKEN")
                print(f"⏳ 等待外部 {name}: {url}")
            else:
                child_env = os.environ.copy()
                child_env["PYTHONUNBUFFERED"] = "1"
                child_env["PYTHONIOENCODING"] = "utf-8"
                processes[name] = await asyncio.to_thread(
                    subprocess.Popen,
                    [sys.executable, "-u", "-m", "backend.app.agents.serve", name, "--port", str(port)],
                    cwd=str(project_root), env=child_env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                )
                recent_logs[name] = deque(maxlen=30)
                log_threads[name] = threading.Thread(
                    target=forward_logs, args=(name, processes[name]), daemon=True
                )
                log_threads[name].start()
                print(f"🚀 启动 {name}: {url}")

            deadline = asyncio.get_running_loop().time() + timeout
            while True:
                process = processes.get(name)
                returncode = process.poll() if process is not None else None
                if returncode is not None:
                    detail = await failure_detail(name)
                    raise RuntimeError(f"{name} 启动失败（退出码 {returncode}）{detail}")
                if await discover(name, url):
                    returncode = process.poll() if process is not None else None
                    if returncode is None:
                        print(f"✅ {name} 已就绪: {url}")
                        break
                    detail = await failure_detail(name)
                    raise RuntimeError(f"{name} 启动失败（退出码 {returncode}）{detail}")
                if asyncio.get_running_loop().time() >= deadline:
                    raise RuntimeError(f"等待 {name} 就绪超时（{timeout} 秒）: {url}")
                await asyncio.sleep(0.5)

        return processes
    except BaseException:
        await stop_local_specialists(processes)
        for thread in log_threads.values():
            await asyncio.to_thread(thread.join, 1)
        raise
