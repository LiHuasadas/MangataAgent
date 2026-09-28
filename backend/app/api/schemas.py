"""Pydantic schemas for the frontend HTTP API."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional conversation title")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata")


class ConversationResponse(BaseModel):
    conversation_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    offset: int
    limit: int


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000, description="User prompt or question")
    request_id: Optional[str] = Field(default=None, description="Optional client request ID for idempotency")
    workspace_id: Optional[str] = Field(default=None, description="Target workspace ID for agent execution")


class MessageItemResponse(BaseModel):
    message_id: str
    conversation_id: str
    user_id: str
    request_id: str
    role: str
    content: str
    sequence: int
    created_at: datetime
    reply_to_message_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageListResponse(BaseModel):
    items: list[MessageItemResponse]
    after_sequence: int
    limit: int


class TurnResponse(BaseModel):
    conversation_id: str
    request_id: str
    status: str
    user_message_id: str
    assistant_message_id: Optional[str] = None
    answer: Optional[str] = None
    agent_results: Optional[list[dict[str, Any]]] = None
    artifacts: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    redis: bool = True
    agent_ready: bool = True
    version: str = "1.0.0"


# Workspace & Project Schemas
class GitCloneRequest(BaseModel):
    repo_url: str = Field(..., description="Git 远程仓库地址 (HTTPS 或 SSH)")
    workspace_id: str = Field("default", description="目标工作空间标识符")
    branch: Optional[str] = Field(None, description="指定分支、Tag 或 Commit")
    depth: int = Field(1, ge=0, description="克隆深度，0 表示完整克隆，默认 1 浅克隆")
    auth_token: Optional[str] = Field(None, description="私有仓库访问令牌 (PAT / Access Token)")
    clean_existing: bool = Field(False, description="若目标工作空间已存在是否先清空")


class GitOperationResponse(BaseModel):
    success: bool
    action: str
    workspace_id: str
    workspace_path: str
    repo_url: str
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    file_count: int
    total_size_bytes: int


class WorkspaceUploadResponse(BaseModel):
    success: bool
    workspace_id: str
    workspace_path: str
    file_count: int
    total_size_bytes: int
    files: list[str] = Field(default_factory=list)
    message: Optional[str] = None


class WorkspaceTreeItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int = 0
    children: Optional[list['WorkspaceTreeItem']] = None
    is_git_root: Optional[bool] = None


class WorkspaceStatusResponse(BaseModel):
    workspace_id: str
    user_id: str
    exists: bool
    absolute_path: str
    file_count: int = 0
    total_size_bytes: int = 0
    is_git_repo: bool = False
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    git_commit_message: Optional[str] = None
    git_author: Optional[str] = None
    git_remote_url: Optional[str] = None


# Authentication Schemas
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名 (3-32位字符)")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码 (至少6位)")
    display_name: Optional[str] = Field(None, max_length=64, description="昵称/显示名")


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="登录密码")


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool = True
    token: str
    user: UserResponse
    message: str = "认证成功"


