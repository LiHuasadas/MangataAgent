"""
用于智能体之间通信的 A2A 客户端。
"""
import asyncio
import json
import uuid
import os
import time
from typing import AsyncIterator, Dict, List, Optional

import httpx
from websockets import connect

from ..types import AgentCard, Artifact, Message, Part, Task, TaskState, TaskStatus, TaskTenantContext, TextPart


class A2AClient:
    """与 A2A 智能体交互的客户端。"""

    def __init__(self, timeout: int = 60, service_token: str | None = None):
        """初始化 A2A 客户端。

        Args:
            timeout: HTTP 请求超时时间（秒）
        """
        self.timeout = timeout
        self.service_token = service_token or os.getenv("A2A_SERVICE_TOKEN")
        self.http_client = httpx.AsyncClient(timeout=timeout)

    def _headers(self, user_id: str) -> dict[str, str]:
        if not self.service_token or not user_id:
            raise ValueError("A2A service token and user identity are required")
        return {"Authorization": f"Bearer {self.service_token}", "X-User-ID": user_id}

    async def close(self):
        """关闭客户端并释放资源。"""
        await self.http_client.aclose()

    async def discover_agent(self, agent_url: str) -> AgentCard:
        """通过拉取 AgentCard 发现智能体能力。

        Args:
            agent_url: 智能体的基础 URL

        Returns:
            描述该智能体能力的名片
        """
        well_known_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"

        response = await self.http_client.get(well_known_url)

        # 如果 HTTP 响应不是成功状态，就立刻抛出异常；成功则什么都不做。
        response.raise_for_status()
        return AgentCard.model_validate(response.json())

    async def send_task(self, agent_url: str, text: str, *,
                        context: TaskTenantContext, task_id: str | None = None,
                        metadata: dict | None = None) -> Task:
        """向智能体发送一个新任务。

        Args:
            agent_url: 智能体的基础 URL
            text: 任务的文本内容

        Returns:
            已创建的任务
        """
        task_id = task_id or str(uuid.uuid4())
        print(f"Sending task to {agent_url} with text: {text}")

        message = Message(parts=[TextPart(text=text)])
        print(f"Message: {message}")
        print(f"Message JSON: {message.model_dump_json()}")

        status = TaskStatus(state=TaskState.SUBMITTED, message=message)
        print(f"Status: {status}")

        task = Task(id=task_id, status=status, tenant_context=context, metadata=metadata or {})
        print(f"Task: {task}")

        task_url = f"{agent_url.rstrip('/')}/tasks"
        print(f"Task URL: {task_url}")
        print(f"Task JSON: {task.model_dump_json()}")

        response = await self.http_client.post(
            task_url,
            json=task.model_dump(mode='json'), headers=self._headers(context.user_id),
        )
        print(f"Response: {response}")

        response.raise_for_status()
        return Task.model_validate(response.json())

    async def get_task(self, agent_url: str, task_id: str, *, user_id: str) -> Task:
        """获取任务的当前状态。

        Args:
            agent_url: 智能体的基础 URL
            task_id: 要查询的任务 ID

        Returns:
            当前任务状态
        """
        task_url = f"{agent_url.rstrip('/')}/tasks/{task_id}"
        response = await self.http_client.get(task_url, headers=self._headers(user_id))

        response.raise_for_status()
        return Task.model_validate(response.json())

    async def cancel_task(self, agent_url: str, task_id: str, *, user_id: str) -> Task:
        """取消一个任务。

        Args:
            agent_url: 智能体的基础 URL
            task_id: 要取消的任务 ID

        Returns:
            状态为已取消的任务
        """
        task_url = f"{agent_url.rstrip('/')}/tasks/{task_id}"

        response = await self.http_client.delete(task_url, headers=self._headers(user_id))
        response.raise_for_status()

        return Task.model_validate(response.json())


    async def update_task(self, agent_url: str, task: Task) -> Task:
        """更新任务（例如任务处于 input-required 时补充输入）。

        Args:
            agent_url: 智能体的基础 URL
            task: 更新后的任务数据

        Returns:
            更新后的任务状态
        """
        task_url = f"{agent_url.rstrip('/')}/tasks/{task.id}"

        response = await self.http_client.put(
            task_url,
            json=task.model_dump(mode='json'),
            headers=self._headers(task.tenant_context.user_id if task.tenant_context else ""),
        )
        response.raise_for_status()

        return Task.model_validate(response.json())

    async def subscribe_to_task(self, agent_url: str, task_id: str, *, user_id: str) -> AsyncIterator[Task]:
        """订阅任务的实时更新。

        Args:
            agent_url: 智能体的基础 URL
            task_id: 要订阅的任务 ID

        Yields:
            发生变更时的任务快照
        """
        ws_url = f"{agent_url.rstrip('/')}/tasks/{task_id}/subscribe".replace("http", "ws")

        async with connect(ws_url, additional_headers=self._headers(user_id)) as websocket:
            while True:
                try:
                    message = await websocket.recv() # 接收任务更新
                    task_update = Task.model_validate(json.loads(message))
                    yield task_update

                    # 到达终态后结束订阅
                    if task_update.status.state in [
                        TaskState.COMPLETED,
                        TaskState.FAILED,
                        TaskState.CANCELLED
                    ]:
                        break

                except asyncio.CancelledError:
                    # 客户端侧取消订阅
                    break
