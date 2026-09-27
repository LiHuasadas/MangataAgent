"""
A2A 多智能体系统的公共类型定义。
"""
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_serializer, field_validator, ValidationInfo


class TaskState(str, Enum):
    """A2A 任务的状态。

    枚举的取值必须保持英文，这是协议约定，不能改成中文。
    submitted: 已提交；working: 处理中；input-required: 等待补充输入；
    completed: 完成；failed: 失败；cancelled: 已取消。
    """
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PartType(str, Enum):
    """A2A 消息中内容片段的类型：text 文本、file 文件、data 结构化数据。"""
    TEXT = "text"
    FILE = "file"
    DATA = "data"


class Part(BaseModel):
    """所有消息片段的基类。"""
    model_config = {'discriminator': 'type'}
    type: PartType


class TextPart(Part):
    """文本内容片段。"""
    type: PartType = PartType.TEXT
    text: str


class FilePart(Part):
    """文件内容片段。"""
    type: PartType = PartType.FILE
    file_name: str
    mime_type: str
    content: bytes


class DataPart(Part):
    """结构化数据内容片段。"""
    type: PartType = PartType.DATA
    data: Dict[str, Any]


class Message(BaseModel):
    """A2A 协议中的一条消息。"""
    parts: List[Union[TextPart, FilePart, DataPart]]

    """
        在把Message
        模型转换为字典或 JSON 时，
        强制将 parts 列表里的每个多态片段都转换为“纯 JSON 兼容的字典”格式，防止报错。
    """
    @field_serializer('parts', mode='plain')
    def serialize_parts(self, parts: List[Union[TextPart, FilePart, DataPart]]):
        return [part.model_dump(mode='json') for part in parts]


class TaskStatus(BaseModel):
    """A2A 任务的状态、message信息。"""
    state: TaskState
    message: Optional[Message] = None
    reason: Optional[str] = None


class ArtifactType(str, Enum):
    """智能体产出的产物类型：document 文档、visualization 可视化、data 数据、plan 计划。"""
    DOCUMENT = "document"
    VISUALIZATION = "visualization"
    DATA = "data"
    PLAN = "plan"
    OTHER = "other"


class Artifact(BaseModel):
    """智能体产出的一份产物（比纯文本更结构化）。"""
    id: str
    type: ArtifactType
    name: str
    description: Optional[str] = None
    content: Any


class TaskTenantContext(BaseModel):
    """Validated context for new tenant-aware tasks; legacy Task remains valid."""

    user_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)


class Task(BaseModel):
    """A2A protocol task. New callers may supply validated tenant context."""

    id: str
    status: TaskStatus
    artifacts: List[Artifact] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tenant_context: Optional[TaskTenantContext] = None


class Skill(BaseModel):
    """智能体能够执行的一项技能。"""
    id: str
    name: str
    description: str


class Capabilities(BaseModel):
    """智能体的能力声明。"""
    streaming: bool = False
    pushNotifications: bool = False


class AgentCard(BaseModel):
    """用于发现的智能体名片（GET /.well-known/agent.json 返回的内容）。

    字段名保持英文，与 A2A 发现协议一致。
    """
    name: str
    description: str
    url: str
    version: str
    capabilities: Capabilities
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    skills: List[Skill]
