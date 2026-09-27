"""Agent基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Optional, TYPE_CHECKING

from fastapi import FastAPI

from .message import Message
from .config import Config
from ..protocols.a2a.server import A2ABaseServer
from ..protocols.types import AgentCard, Task, TaskState, TextPart, Message as A2AMessage

if TYPE_CHECKING:
    from .llm import HelloAgentsLLM


class Agent(A2ABaseServer):
    """Agent基类"""
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        agent_card: AgentCard,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        app: Optional[FastAPI] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []
        self._task_lock = asyncio.Lock()
        self._memory_scopes = {}
        super().__init__(
            agent_card=agent_card,
            app=app
        )

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent"""
        pass
    
    def add_message(self, message: Message):
        """添加消息到历史记录"""
        self._history.append(message)
    
    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
    
    def get_history(self) -> list[Message]:
        """获取历史记录"""
        return self._history.copy()

    def call_tool(self, name: str, input_text: str) -> str:
        """Expose registered tools to an Agent's orchestration logic."""
        registry = getattr(self, "tool_registry", None)
        if registry is None:
            raise RuntimeError("Agent has no tool registry")
        return registry.execute_tool(name, input_text)

    def load_history(self, messages: list[Message]) -> None:
        """加载一个会话的历史，避免与调用方共享可变消息对象。"""
        self._history = [message.model_copy(deep=True) for message in messages]

    async def handle_task(self, task: Task) -> Task:
        """Run an existing synchronous Agent through the A2A service."""
        context = task.tenant_context
        if context is None:
            raise ValueError("Task tenant context is required")
        input_text = "\n".join(
            part.text for part in (task.status.message.parts if task.status.message else [])
            if isinstance(part, TextPart)
        )
        if not input_text.strip():
            raise ValueError("Task text is required")
        async with self._task_lock:
            previous_history = self._history
            previous_memory = getattr(self, "memory_tool", None)
            self._history = []
            try:
                if previous_memory is not None:
                    from ..tools.builtin import MemoryTool
                    scope = (context.user_id, context.conversation_id)
                    if scope not in self._memory_scopes:
                        self._memory_scopes[scope] = MemoryTool(
                            user_id=context.user_id,
                            conversation_id=context.conversation_id,
                            memory_types=previous_memory.memory_types,
                            memory_config=previous_memory.memory_config,
                        )
                    self.memory_tool = self._memory_scopes[scope]
                    if hasattr(self, "context_builder"):
                        self.context_builder.memory_tool = self.memory_tool
                    self.add_tool(self.memory_tool)
                answer = await asyncio.to_thread(self.run, input_text)
            finally:
                self._history = previous_history
                if previous_memory is not None:
                    self.memory_tool = previous_memory
                    if hasattr(self, "context_builder"):
                        self.context_builder.memory_tool = previous_memory
                    self.add_tool(previous_memory)
        task.status.state = TaskState.COMPLETED
        task.status.message = A2AMessage(parts=[TextPart(text=str(answer))])
        return task
    
    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
    
    def __repr__(self) -> str:
        return self.__str__()
