"""Models shared by the Redis repository and future API layer."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from ..core.message import ChatMessage


class TurnStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("conversation time must include a timezone")
        return value.astimezone(timezone.utc)


class Turn(BaseModel):
    conversation_id: str
    request_id: str
    status: TurnStatus
    user_message_id: str
    assistant_message_id: str | None = None
    lock_token: str | None = Field(default=None, exclude=True)
    error: str | None = None


class ConversationNotFound(Exception):
    pass


class MessageNotFound(Exception):
    pass


class RequestConflict(Exception):
    pass


class ConversationBusy(Exception):
    pass


class LeaseLost(Exception):
    pass


class TurnStateConflict(Exception):
    pass
