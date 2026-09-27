"""
实现 A2A 智能体时使用的服务端基类。
"""
import asyncio
import json
import uuid
import os
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..types import AgentCard, Artifact, Message, Task, TaskState, TaskStatus, TextPart


class TaskUpdate(BaseModel):
    """一次任务更新。"""
    task_id: str
    task: Task


class A2ABaseServer(ABC):
    """A2A 服务端实现的基类。"""

    def __init__(
        self,
        agent_card: AgentCard,
        app: Optional[FastAPI] = None,
    ):
        """初始化 A2A 服务端。

        Args:
            agent_card: 描述本智能体的名片
            app: 可选的 FastAPI 应用；不传则自动创建
        """
        self.agent_card = agent_card
        self.app = app or FastAPI(title=agent_card.name)

        self.tasks: Dict[str, Task] = {}
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self.submissions: Dict[str, Task] = {}

        # 注册路由
        self._register_routes()

    def _register_routes(self):
        """注册 A2A 服务端路由。"""

        # 智能体名片发现
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            # 模型对象 转成字典 并返回。
            return self.agent_card.model_dump()

        # 任务管理
        @self.app.post("/tasks")
        async def create_task(task: Dict[str, Any], request: Request):
            user_id = self._authorize(request.headers)
            print(f"Task: {task}")

            # 把 `task` 数据 校验并转成 `Task` 模型实例（字段类型完全相同）
            task_obj = Task.model_validate(task)
            if task_obj.tenant_context is None or task_obj.tenant_context.user_id != user_id:
                raise HTTPException(status_code=404, detail="Task not found")
            print(f"Task object: {task_obj}")
            # 校验任务状态：新建任务必须是 submitted
            if task_obj.status.state != TaskState.SUBMITTED:
                raise HTTPException(
                    status_code=400,
                    detail="New tasks must have 'submitted' state"
                )

            # 保存任务
            existing = self.tasks.get(task_obj.id)
            if existing is not None:
                original = self.submissions[task_obj.id]
                if existing.tenant_context.user_id != user_id:
                    raise HTTPException(status_code=404, detail="Task not found")
                if (original.tenant_context != task_obj.tenant_context or
                    original.status.message != task_obj.status.message):
                    raise HTTPException(status_code=409, detail="Task ID already used")
                return existing.model_dump()
            self.submissions[task_obj.id] = task_obj.model_copy(deep=True)
            self.tasks[task_obj.id] = task_obj

            # 后台开始处理任务
            task_obj = await self._update_task_state(
                task_obj, #
                TaskState.WORKING,
                task_obj.status.message
            )

            self.background_tasks[task_obj.id] = asyncio.create_task(self._process_task(task_obj))

            return task_obj.model_dump()

        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str, request: Request):
            user_id = self._authorize(request.headers)
            self._check_owner(task_id, user_id)
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return self.tasks[task_id].model_dump()

        @self.app.put("/tasks/{task_id}")
        async def update_task(task_id: str, task: Dict[str, Any], request: Request):
            user_id = self._authorize(request.headers)
            self._check_owner(task_id, user_id)
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")

            updated_task = Task.model_validate(task)
            if updated_task.id != task_id or updated_task.tenant_context != self.tasks[task_id].tenant_context:
                raise HTTPException(status_code=409, detail="Task context cannot change")

            # 校验状态迁移：只有等待补充输入的任务才允许更新
            current_task = self.tasks[task_id]
            if current_task.status.state != TaskState.INPUT_REQUIRED:
                raise HTTPException(
                    status_code=400,
                    detail="Only tasks in 'input-required' state can be updated"
                )

            # 更新任务并继续处理
            self.tasks[task_id] = updated_task
            updated_task = await self._update_task_state(
                updated_task,
                TaskState.WORKING,
                updated_task.status.message
            )

            # 继续后台处理
            self.background_tasks[task_id] = asyncio.create_task(self._process_task(updated_task))

            return updated_task.model_dump()

        @self.app.delete("/tasks/{task_id}")
        async def cancel_task(task_id: str, request: Request):
            user_id = self._authorize(request.headers)
            self._check_owner(task_id, user_id)
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")

            task = self.tasks[task_id]
            self.stop_task(task_id)
            background = self.background_tasks.get(task_id)
            if background:
                background.cancel()
            task = await self._update_task_state(
                task,
                TaskState.CANCELLED,
                task.status.message,
                "Task cancelled by client"
            )
            return task.model_dump()

        @self.app.websocket("/tasks/{task_id}/subscribe")
        async def subscribe_to_task(websocket: WebSocket, task_id: str):
            try:
                user_id = self._authorize(websocket.headers)
                self._check_owner(task_id, user_id)
            except HTTPException:
                await websocket.close(code=1008)
                return
            if task_id not in self.tasks:
                await websocket.close(code=1000, reason="Task not found")
                return

            await websocket.accept() # 接受 WebSocket 连接

            # 加入该任务的订阅者集合
            if task_id not in self.task_subscribers:
                self.task_subscribers[task_id] = set()

            self.task_subscribers[task_id].add(websocket) # 加入订阅者集合

            try:
                # 立刻把当前状态发给客户端
                await websocket.send_text(self.tasks[task_id].model_dump_json())

                # 保持连接，直到客户端断开
                while True:
                    # 会阻塞直到客户端发消息或断开
                    # 通常客户端只监听、不发送数据
                    await websocket.receive_text()

            except WebSocketDisconnect:
                # 从订阅者中移除
                if task_id in self.task_subscribers:
                    self.task_subscribers[task_id].discard(websocket)

                    if not self.task_subscribers[task_id]:
                        del self.task_subscribers[task_id]

    async def _notify_subscribers(self, task_id: str, task: Task):
        """把任务更新通知给所有订阅者。

        Args:
            task_id: 被更新的任务 ID
            task: 更新后的任务数据
        """
        if task_id not in self.task_subscribers:
            return

        dead_subscribers = set()

        # 序列化任务更新
        task_json = task.model_dump_json()

        # 向所有订阅者发送更新
        for websocket in self.task_subscribers[task_id]:
            try:
                await websocket.send_text(task_json)
            except RuntimeError:
                # WebSocket 可能已经关闭
                dead_subscribers.add(websocket)

        # 清理已失效的订阅者
        # `-=` — 集合的**差集赋值**，从原集合中移除右边集合里的所有元素
        self.task_subscribers[task_id] -= dead_subscribers

        if not self.task_subscribers[task_id]:
            del self.task_subscribers[task_id]

    async def _update_task_state(
        self,
        task: Task,
        state: TaskState,
        message: Optional[Message] = None,
        reason: Optional[str] = None
    ) -> Task:
        """更新任务状态并通知订阅者。

        Args:
            task: 要更新的任务
            state: 新状态
            message: 可选的新消息
            reason: 可选的状态变更原因

        Returns:
            更新后的任务
        """
        task.status.state = state
        if message:
            task.status.message = message
        if reason:
            task.status.reason = reason

        # 写回内存中的任务表
        self.tasks[task.id] = task

        # 更新任务状态、通知订阅者
        await self._notify_subscribers(task.id, task)

        return task

    async def _process_task(self, task: Task):
        """在后台处理任务。

        本方法会调用抽象方法 handle_task，并处理错误与状态迁移。

        Args:
            task: 要处理的任务
        """
        try:
            result_task = await self.handle_task(task)

            if result_task.status.state not in [
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.CANCELLED,
                TaskState.INPUT_REQUIRED
            ]:
                # 子类未设置终态时，默认视为已完成
                await self._update_task_state(
                    result_task,
                    TaskState.COMPLETED,
                    result_task.status.message
                )

            else:
                # 确保状态已保存，并通知订阅者
                await self._update_task_state(
                    result_task,
                    result_task.status.state,
                    result_task.status.message,
                    result_task.status.reason
                )
        except asyncio.CancelledError:
            await self._update_task_state(task, TaskState.CANCELLED, task.status.message,
                                          "Task cancelled")
        except Exception as e:
            # 捕获未处理异常，将任务标为失败
            error_message = Message(
                parts=[TextPart(text=f"Error processing task: {str(e)}")]
            )
            await self._update_task_state(
                task,
                TaskState.FAILED,
                error_message,
                str(e)
            )
        finally:
            self.background_tasks.pop(task.id, None)

    @staticmethod
    def _authorize(headers) -> str:
        expected = os.getenv("A2A_SERVICE_TOKEN")
        if not expected:
            raise HTTPException(status_code=503, detail="A2A service token is not configured")
        provided = headers.get("authorization", "")
        if not provided.startswith("Bearer ") or not secrets.compare_digest(provided[7:], expected):
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_id = headers.get("x-user-id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="User identity is required")
        return user_id

    def _check_owner(self, task_id: str, user_id: str) -> None:
        task = self.tasks.get(task_id)
        if task is None or task.tenant_context is None or task.tenant_context.user_id != user_id:
            raise HTTPException(status_code=404, detail="Task not found")

    def stop_task(self, task_id: str) -> None:
        """Request cooperative cancellation; request-local Agents override this."""

    # **抽象方法**的装饰器，标记这个方法**必须由子类实现**，
    @abstractmethod
    async def handle_task(self, task: Task) -> Task:
        """处理任务。

        子类必须实现本方法。应返回带有合适状态和产物的更新后任务。

        Args:
            task: 要处理的任务

        Returns:
            带有处理结果的任务
        """
        pass
