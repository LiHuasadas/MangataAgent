"""Exercise the original five Agent designs with deterministic tool responses."""

import asyncio
import sys
from types import SimpleNamespace

import pytest

from backend.app.agents.host_agent import HostAgent
from backend.app.agents.plan_solve_agent import PlanAndSolveAgent
from backend.app.agents.react_agent import ContextAwareAgent
from backend.app.agents.reflection_agent import ReflectionAgent
from backend.app.agents.simple_agent import SimpleAgent
from backend.app.context import ContextBuilder
from backend.app.core.llm import HelloAgentsLLM
from backend.app.memory.types.semantic import SemanticMemory
from backend.app.memory.types import perceptual as perceptual_module
from backend.app.memory.base import MemoryConfig
from backend.app.protocols.types import (
    Message, Task, TaskState, TaskStatus, TaskTenantContext, TextPart,
)
from backend.app.tools.builtin import MCPTool, TerminalTool


class ScriptedLLM:
    provider = "test"

    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def invoke(self, messages, **kwargs):
        self.calls.append(messages)
        return next(self.responses)

    def call(self, messages, **kwargs):
        self.calls.append(messages)
        return next(self.responses)


@pytest.fixture(autouse=True)
def simple_context(monkeypatch):
    monkeypatch.setattr(
        ContextBuilder, "build",
        lambda self, user_query, conversation_history, system_instructions=None, **kwargs:
            f"{system_instructions or ''}\n{user_query}",
    )


def test_every_specialist_can_call_a_real_tool(tmp_path):
    scripted = [
        (PlanAndSolveAgent, ('["检查事实"]',
                             'Action: terminal[{"command":"echo evidence"}]',
                             'Finish[依据 evidence，检查已完成]')),
        (SimpleAgent, ('[TOOL_CALL:terminal:command=echo evidence]',
                       '依据 evidence，给出回答')),
        (ContextAwareAgent, ('Thought: 先检查\nAction: terminal[{"command":"echo evidence"}]',
                             'Thought: 已有结果\nAction: Finish[依据 evidence，给出回答]')),
        (ReflectionAgent, ('Action: terminal[{"command":"echo evidence"}]',
                           'Finish[依据 evidence，初稿完成]', '无需改进')),
    ]
    for agent_type, responses in scripted:
        llm = ScriptedLLM(*responses)
        agent = agent_type(agent_type.__name__, llm, user_id="alice", workspace=str(tmp_path))
        assert "terminal" in agent.tool_registry.list_tools()
        answer = agent.run("检查后回答")
        assert "evidence" in answer
        assert any("evidence" in str(call) for call in llm.calls[1:])


def test_host_routes_all_four_agents_sequentially_with_tenant_context(tmp_path):
    llm = ScriptedLLM('["plan_solve_agent", "reflection_agent"]', "汇总：有实际结果")
    host = HostAgent("host", llm, user_id="alice", knowledge_base_path=str(tmp_path),
                     rag_namespace="test", workspace=str(tmp_path))
    assert "terminal" in host.tool_registry.list_tools()
    sent = []

    async def fake_call(agent_type, message, context):
        sent.append((agent_type, message, context.user_id))
        return {"agent_type": agent_type, "success": True,
                "response": f"{agent_type} 的事实结果", "artifacts": []}

    host._call_agent = fake_call
    context = TaskTenantContext(user_id="alice", conversation_id="c1",
                                request_id="r1", workspace_id="w1")
    task = Task(id="t1", tenant_context=context,
                status=TaskStatus(state=TaskState.SUBMITTED,
                                  message=Message(parts=[TextPart(text="分析并检查")])) )
    events = []

    async def on_progress(event):
        events.append(event)

    result = asyncio.run(host.handle_task(task, progress_callback=on_progress))
    assert result.status.state == TaskState.COMPLETED
    assert [item[0] for item in sent] == ["plan_solve_agent", "reflection_agent"]
    assert "plan_solve_agent 的事实结果" in sent[1][1]
    assert all(item[2] == "alice" for item in sent)
    assert len(result.metadata["agent_results"]) == 2
    assert [event["stage"] for event in events if event["type"] == "progress"] == [
        "preparing", "routing", "routed", "agent_started", "agent_finished",
        "agent_started", "agent_finished", "consolidating",
    ]
    assert [event["agent_type"] for event in events if event["type"] == "agent_result"] == [
        "plan_solve_agent", "reflection_agent",
    ]


def test_host_rejects_turn_when_all_selected_agents_fail(tmp_path):
    llm = ScriptedLLM('["simple_agent"]')
    host = HostAgent("host", llm, user_id="alice", knowledge_base_path=str(tmp_path),
                     rag_namespace="test", workspace=str(tmp_path))

    async def unavailable(agent_type, message, context):
        return {"agent_type": agent_type, "success": False,
                "response": "All connection attempts failed", "artifacts": []}

    host._call_agent = unavailable
    context = TaskTenantContext(user_id="alice", conversation_id="c1",
                                request_id="r1", workspace_id="w1")
    task = Task(id="t-failed", tenant_context=context,
                status=TaskStatus(state=TaskState.SUBMITTED,
                                  message=Message(parts=[TextPart(text="hello")])))

    with pytest.raises(RuntimeError, match="simple_agent: All connection attempts failed"):
        asyncio.run(host.handle_task(task))


def test_llm_call_adapter_uses_invoke_message_format():
    seen = []
    llm = HelloAgentsLLM.__new__(HelloAgentsLLM)
    llm.model = "test"
    llm.temperature = 0.7
    llm.max_tokens = None
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: (seen.append(kwargs) or SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])))))

    assert llm.call("hello") == "ok"
    assert seen[0]["messages"] == [{"role": "user", "content": "hello"}]


def test_graph_search_accepts_legacy_entity_without_types():
    memory = SemanticMemory.__new__(SemanticMemory)
    memory._extract_entities = lambda query: []
    memory.graph_store = SimpleNamespace(
        search_entities_by_name=lambda **kwargs: [{"id": "legacy", "name": "Legacy"}],
        find_related_entities=lambda **kwargs: [],
        get_entity_relationships=lambda entity_id: [],
    )

    assert memory._graph_search("Legacy", limit=10) == []


def test_perceptual_memory_loads_cached_models_on_first_modality_use(monkeypatch, tmp_path):
    model_calls = []
    store_calls = []

    def load_model(name, **kwargs):
        model_calls.append((name, kwargs))
        return SimpleNamespace(config=SimpleNamespace(projection_dim=512))

    fake_transformers = SimpleNamespace(
        CLIPModel=SimpleNamespace(from_pretrained=load_model),
        CLIPProcessor=SimpleNamespace(from_pretrained=load_model),
        ClapModel=SimpleNamespace(from_pretrained=load_model),
        ClapProcessor=SimpleNamespace(from_pretrained=load_model),
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.delenv("PERCEPTUAL_ALLOW_MODEL_DOWNLOAD", raising=False)
    monkeypatch.setattr(perceptual_module, "get_text_embedder", lambda: SimpleNamespace(dimension=384))
    monkeypatch.setattr(perceptual_module, "SQLiteDocumentStore", lambda **kwargs: object())
    from backend.app.memory.storage.qdrant_store import QdrantConnectionManager
    def get_store(**kwargs):
        store_calls.append(kwargs)
        return object()

    monkeypatch.setattr(QdrantConnectionManager, "get_instance", get_store)

    memory = perceptual_module.PerceptualMemory(MemoryConfig(storage_path=str(tmp_path)))

    assert model_calls == []
    assert len(store_calls) == 1
    assert store_calls[0]["collection_name"].endswith("_perceptual_text")
    assert len(memory._encode_data("missing-image.png", "image")) == 512
    assert len(model_calls) == 2
    assert len(store_calls) == 2
    assert store_calls[-1]["vector_size"] == 512
    assert len(memory._encode_data("missing-audio.wav", "audio")) == 512
    assert len(model_calls) == 4
    assert len(store_calls) == 3
    assert all(kwargs["local_files_only"] is True for _, kwargs in model_calls)
    assert memory._get_dim_for_modality("image") == 512


def test_specialist_a2a_request_rebinds_user_and_conversation(tmp_path):
    llm = ScriptedLLM("为 alice 的会话提供回答")
    agent = SimpleAgent("simple", llm, user_id="initial", workspace=str(tmp_path))
    original_memory = agent.memory_tool
    context = TaskTenantContext(user_id="alice", conversation_id="c1",
                                request_id="r1", workspace_id="w1")
    task = Task(id="t1", tenant_context=context,
                status=TaskStatus(state=TaskState.SUBMITTED,
                                  message=Message(parts=[TextPart(text="你好")])) )
    result = asyncio.run(agent.handle_task(task))
    assert result.status.state == TaskState.COMPLETED
    assert result.status.message.parts[0].text == "为 alice 的会话提供回答"
    assert agent.memory_tool is original_memory
    assert agent.get_history() == []


def test_terminal_does_not_interpret_shell_operators(tmp_path):
    terminal = TerminalTool(workspace=str(tmp_path))
    output = terminal.run({"command": "echo evidence & echo injected"})
    assert output == "evidence & echo injected"


def test_generic_mcp_tool_remains_callable():
    from fastmcp import FastMCP

    server = FastMCP("agent-tool-test")

    @server.tool
    def echo(text: str) -> str:
        return f"MCP evidence: {text}"

    tool = MCPTool(name="local", server=server, auto_expand=False)
    result = tool.run({"action": "call_tool", "tool_name": "echo",
                       "arguments": {"text": "works"}})
    assert "MCP evidence: works" in result


def test_a2a_working_memory_scope_is_reused_only_within_same_conversation(tmp_path):
    agent = SimpleAgent("simple", ScriptedLLM("a", "b", "c"),
                        user_id="initial", workspace=str(tmp_path))

    def run_task(user_id, conversation_id, request_id):
        task = Task(
            id=request_id,
            tenant_context=TaskTenantContext(
                user_id=user_id, conversation_id=conversation_id,
                request_id=request_id, workspace_id="w1",
            ),
            status=TaskStatus(state=TaskState.SUBMITTED,
                              message=Message(parts=[TextPart(text="hello")])),
        )
        asyncio.run(agent.handle_task(task))

    run_task("alice", "one", "r1")
    first = agent._memory_scopes[("alice", "one")]
    assert "已添加" in first.execute("add", content="private evidence", memory_type="working")
    run_task("alice", "one", "r2")
    assert agent._memory_scopes[("alice", "one")] is first
    run_task("alice", "two", "r3")
    assert agent._memory_scopes[("alice", "two")] is not first
    assert not agent._memory_scopes[("alice", "two")].memory_manager.memory_types["working"].memories


def test_a2a_workspace_dynamic_isolation(tmp_path):
    llm = ScriptedLLM('Action: terminal[{"command":"echo hello_user"}]', 'Finish[done]')
    agent = ContextAwareAgent("coder", llm, user_id="initial", workspace=str(tmp_path))
    original_workspace = agent.terminal.workspace

    context = TaskTenantContext(user_id="user_bob", conversation_id="conv_1",
                                request_id="req_1", workspace_id="ws_bob")
    task = Task(
        id="t_ws",
        tenant_context=context,
        status=TaskStatus(state=TaskState.SUBMITTED, message=Message(parts=[TextPart(text="write code")])),
    )
    result = asyncio.run(agent.handle_task(task))
    assert result.status.state == TaskState.COMPLETED
    assert agent.terminal.workspace == original_workspace
    user_isolated_dir = tmp_path / "user_bob" / "ws_bob"
    assert user_isolated_dir.exists()


def test_reflection_agent_executes_validation_command_from_metadata(tmp_path):
    llm = ScriptedLLM("初稿代码", "无需改进")
    agent = ReflectionAgent("tester", llm, user_id="alice", workspace=str(tmp_path))

    context = TaskTenantContext(user_id="alice", conversation_id="c1",
                                request_id="r1", workspace_id="w1")
    task = Task(
        id="t_val",
        tenant_context=context,
        status=TaskStatus(state=TaskState.SUBMITTED, message=Message(parts=[TextPart(text="审查代码")])),
        metadata={"validation_command": "echo test_passed"},
    )
    result = asyncio.run(agent.handle_task(task))
    assert result.status.state == TaskState.COMPLETED
    reply_text = result.status.message.parts[0].text
    assert "test_passed" in reply_text
