"""Trusted caller boundary for conversation storage; no HTTP or Agent calls."""

from ..core.message import ChatMessage
from .models import Conversation, Turn
from .repository import RedisConversationRepository


class ChatService:
    def __init__(self, repository: RedisConversationRepository):
        self.repository = repository

    def create_conversation(self, user_id: str) -> Conversation:
        return self.repository.create_conversation(user_id)

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        return self.repository.get_conversation(user_id, conversation_id)

    def list_conversations(self, user_id: str, offset: int = 0, limit: int = 20) -> list[Conversation]:
        return self.repository.list_conversations(user_id, offset, limit)

    def get_message(self, user_id: str, conversation_id: str, message_id: str) -> ChatMessage:
        return self.repository.get_message(user_id, conversation_id, message_id)

    def list_messages(self, user_id: str, conversation_id: str, after_sequence: int = 0,
                      limit: int = 20) -> list[ChatMessage]:
        return self.repository.list_messages(user_id, conversation_id, after_sequence, limit)

    def list_recent_messages(self, user_id: str, conversation_id: str,
                             limit: int = 50) -> list[ChatMessage]:
        return self.repository.list_recent_messages(user_id, conversation_id, limit)

    def get_turn(self, user_id: str, conversation_id: str, request_id: str) -> Turn | None:
        return self.repository.get_turn(user_id, conversation_id, request_id)

    def begin_turn(self, user_id: str, conversation_id: str, request_id: str, content: str) -> Turn:
        return self.repository.begin_turn(user_id, conversation_id, request_id, content)

    def complete_turn(self, user_id: str, conversation_id: str, request_id: str,
                      lock_token: str, content: str) -> Turn:
        return self.repository.complete_turn(user_id, conversation_id, request_id, lock_token, content)

    def fail_turn(self, user_id: str, conversation_id: str, request_id: str,
                  lock_token: str, error: str) -> Turn:
        return self.repository.fail_turn(user_id, conversation_id, request_id, lock_token, error)

    def renew_turn(self, user_id: str, conversation_id: str, request_id: str,
                   lock_token: str) -> None:
        self.repository.renew_turn(user_id, conversation_id, request_id, lock_token)
