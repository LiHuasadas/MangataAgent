"""Exercise the original five Agent designs with deterministic tool responses."""

import asyncio

import pytest

from backend.app.agents.host_agent import HostAgent
from backend.app.agents.plan_solve_agent import PlanAndSolveAgent
from backend.app.agents.react_agent import ContextAwareAgent
from backend.app.agents.reflection_agent import ReflectionAgent
from backend.app.agents.simple_agent import SimpleAgent
from backend.app.context import ContextBuilder
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
    result = asyncio.run(host.handle_task(task))
    assert result.status.state == TaskState.COMPLETED
    assert [item[0] for item in sent] == ["plan_solve_agent", "reflection_agent"]
    assert "plan_solve_agent 的事实结果" in sent[1][1]
    assert all(item[2] == "alice" for item in sent)
    assert len(result.metadata["agent_results"]) == 2


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
