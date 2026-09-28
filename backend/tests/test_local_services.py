"""Exercise local A2A process ownership without launching model services."""

import asyncio
from io import StringIO
import os
from types import SimpleNamespace

import pytest

from backend.app.agents import local_services


class FakeProcess:
    def __init__(self, returncode=None, output=""):
        self.returncode = returncode
        self.terminated = False
        self.stdout = StringIO(output)

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.returncode = -9

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


def test_main_starts_missing_local_specialists_and_stops_owned_processes(monkeypatch, tmp_path):
    launched = {}
    probes = {}

    async def discover(url):
        name = "plan_solve_agent" if url.endswith("8001") else "simple_agent"
        probes[name] = probes.get(name, 0) + 1
        if name == "plan_solve_agent" and probes[name] < 3:
            assert "simple_agent" not in launched
            raise ConnectionError("not ready")
        if name not in launched:
            raise ConnectionError("not ready")
        return SimpleNamespace(name=name)

    def spawn(args, **kwargs):
        name = args[4]
        process = FakeProcess()
        launched[name] = process
        assert args[-2:] == ["--port", "8001" if name == "plan_solve_agent" else "8004"]
        assert kwargs["stderr"] == local_services.subprocess.STDOUT
        assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
        return process

    monkeypatch.setattr(local_services.subprocess, "Popen", spawn)

    async def unsupported(*args, **kwargs):
        raise NotImplementedError("Windows selector event loop")

    monkeypatch.setattr(local_services.asyncio, "create_subprocess_exec", unsupported)
    host = SimpleNamespace(
        client=SimpleNamespace(discover_agent=discover),
        agent_urls={"plan_solve_agent": "http://localhost:8001",
                    "simple_agent": "http://127.0.0.1:8004"},
        agent_capabilities={},
    )

    async def run():
        processes = await local_services.start_local_specialists(host, tmp_path)
        assert set(processes) == {"plan_solve_agent", "simple_agent"}
        assert set(host.agent_capabilities) == set(processes)
        await local_services.stop_local_specialists(processes)

    asyncio.run(run())
    assert all(process.terminated for process in launched.values())


def test_main_reuses_existing_specialist(monkeypatch, tmp_path):
    async def discover(url):
        return SimpleNamespace(name="Simple Agent")

    def unexpected_spawn(*args, **kwargs):
        pytest.fail("existing specialist must not be restarted")

    monkeypatch.setattr(local_services.subprocess, "Popen", unexpected_spawn)
    host = SimpleNamespace(
        client=SimpleNamespace(discover_agent=discover),
        agent_urls={"simple_agent": "http://localhost:8004"},
        agent_capabilities={},
    )
    assert asyncio.run(local_services.start_local_specialists(host, tmp_path)) == {}
    assert "simple_agent" in host.agent_capabilities


def test_new_token_rejects_existing_specialist(tmp_path):
    async def discover(url):
        return SimpleNamespace(name="Simple Agent")

    host = SimpleNamespace(
        client=SimpleNamespace(discover_agent=discover),
        agent_urls={"simple_agent": "http://localhost:8004"},
        agent_capabilities={},
    )
    with pytest.raises(RuntimeError, match="配置相同的 A2A_SERVICE_TOKEN"):
        asyncio.run(local_services.start_local_specialists(host, tmp_path, reuse_existing=False))


def test_child_exit_fails_gateway_startup(monkeypatch, tmp_path):
    async def discover(url):
        raise ConnectionError("not ready")

    def spawn(*args, **kwargs):
        return FakeProcess(returncode=2, output="Traceback: MemoryError\n")

    monkeypatch.setattr(local_services.subprocess, "Popen", spawn)
    host = SimpleNamespace(
        client=SimpleNamespace(discover_agent=discover),
        agent_urls={"simple_agent": "http://localhost:8004"},
        agent_capabilities={},
    )
    with pytest.raises(RuntimeError, match="simple_agent 启动失败（退出码 2）.*") as error:
        asyncio.run(local_services.start_local_specialists(host, tmp_path))
    assert "[simple_agent] Traceback: MemoryError" in str(error.value)


def test_later_child_failure_stops_earlier_child(monkeypatch, tmp_path):
    launched = {}

    async def discover(url):
        if url.endswith("8001") and "plan_solve_agent" in launched:
            return SimpleNamespace(name="plan_solve_agent")
        raise ConnectionError("not ready")

    def spawn(args, **kwargs):
        name = args[4]
        process = FakeProcess(returncode=1 if name == "reflection_agent" else None)
        launched[name] = process
        return process

    monkeypatch.setattr(local_services.subprocess, "Popen", spawn)
    host = SimpleNamespace(
        client=SimpleNamespace(discover_agent=discover),
        agent_urls={"plan_solve_agent": "http://localhost:8001",
                    "reflection_agent": "http://localhost:8003"},
        agent_capabilities={},
    )
    with pytest.raises(RuntimeError, match="reflection_agent 启动失败（退出码 1）"):
        asyncio.run(local_services.start_local_specialists(host, tmp_path))
    assert launched["plan_solve_agent"].terminated


def test_main_lifespan_generates_shared_token_and_stops_children(monkeypatch):
    from backend.app import main as gateway
    from backend.app.core import auth_service, workspace_service

    monkeypatch.setenv("AUTO_START_SPECIALISTS", "true")
    monkeypatch.delenv("A2A_SERVICE_TOKEN", raising=False)
    closed = []
    fake_redis = SimpleNamespace(ping=lambda: True, close=lambda: closed.append("redis"))

    async def close_client():
        closed.append("client")

    fake_host = SimpleNamespace(client=SimpleNamespace(close=close_client))
    monkeypatch.setattr(gateway.Redis, "from_url", staticmethod(lambda *args, **kwargs: fake_redis))
    monkeypatch.setattr(gateway, "create_host_agent", lambda: fake_host)
    monkeypatch.setattr(workspace_service, "WorkspaceService", lambda **kwargs: object())
    monkeypatch.setattr(auth_service, "AuthService", lambda client: object())

    async def start(host_agent, project_root, *, reuse_existing):
        assert host_agent is fake_host
        assert os.environ["A2A_SERVICE_TOKEN"]
        assert reuse_existing is False
        return {"simple_agent": FakeProcess()}

    async def stop(processes):
        assert "simple_agent" in processes
        closed.append("specialist")

    monkeypatch.setattr(gateway, "start_local_specialists", start)
    monkeypatch.setattr(gateway, "stop_local_specialists", stop)
    app = SimpleNamespace(state=SimpleNamespace())

    async def run():
        async with gateway.lifespan(app):
            assert app.state.host_agent is fake_host

    asyncio.run(run())
    assert closed == ["specialist", "client", "redis"]
