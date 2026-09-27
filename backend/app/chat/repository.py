"""Redis-backed, tenant-scoped conversation repository.

Every key touched by a turn script has the same user hash tag. Processing
records intentionally have no TTL: an expired lease becomes UNKNOWN and must
be reconciled before anyone attempts the side-effectful work again.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from redis import Redis

from ..core.message import ChatMessage
from .config import ChatRedisConfig
from .models import (
    Conversation, ConversationBusy, ConversationNotFound, LeaseLost,
    MessageNotFound, RequestConflict, Turn, TurnStateConflict, TurnStatus,
)


BEGIN_SCRIPT = """
if redis.call('HGET', KEYS[1], 'user_id') ~= ARGV[1] then return {'NOT_FOUND'} end
local status = redis.call('HGET', KEYS[5], 'status')
if status then
    if redis.call('HGET', KEYS[5], 'fingerprint') ~= ARGV[2] then return {'CONFLICT'} end
    if status == 'PROCESSING' and redis.call('GET', KEYS[4]) ~= redis.call('HGET', KEYS[5], 'token') then
        redis.call('HSET', KEYS[5], 'status', 'UNKNOWN')
        status = 'UNKNOWN'
    end
    return {status, redis.call('HGET', KEYS[5], 'user_message_id'),
        redis.call('HGET', KEYS[5], 'assistant_message_id') or '',
        redis.call('HGET', KEYS[5], 'error') or ''}
end
if not redis.call('SET', KEYS[4], ARGV[3], 'NX', 'PX', ARGV[4]) then return {'BUSY'} end
local seq = redis.call('HINCRBY', KEYS[1], 'last_sequence', 1)
local message = cjson.decode(ARGV[7])
message.sequence = seq
redis.call('HSET', KEYS[2], ARGV[5], cjson.encode(message))
redis.call('ZADD', KEYS[3], seq, ARGV[5])
redis.call('HSET', KEYS[1], 'updated_at', ARGV[8])
redis.call('ZADD', KEYS[6], ARGV[9], ARGV[6])
redis.call('HSET', KEYS[5], 'status', 'PROCESSING', 'fingerprint', ARGV[2],
    'conversation_id', ARGV[6], 'user_message_id', ARGV[5], 'token', ARGV[3])
return {'PROCESSING_NEW', ARGV[5]}
"""

COMPLETE_SCRIPT = """
if redis.call('HGET', KEYS[1], 'user_id') ~= ARGV[1] then return {'NOT_FOUND'} end
if redis.call('GET', KEYS[4]) ~= ARGV[2] then return {'LEASE_LOST'} end
if redis.call('HGET', KEYS[5], 'status') ~= 'PROCESSING' or
    redis.call('HGET', KEYS[5], 'token') ~= ARGV[2] then return {'STATE_CONFLICT'} end
local seq = redis.call('HINCRBY', KEYS[1], 'last_sequence', 1)
local message = cjson.decode(ARGV[4])
message.sequence = seq
redis.call('HSET', KEYS[2], ARGV[3], cjson.encode(message))
redis.call('ZADD', KEYS[3], seq, ARGV[3])
redis.call('HSET', KEYS[1], 'updated_at', ARGV[5])
redis.call('ZADD', KEYS[6], ARGV[6], ARGV[7])
redis.call('HSET', KEYS[5], 'status', 'COMPLETED', 'assistant_message_id', ARGV[3])
redis.call('HDEL', KEYS[5], 'token')
redis.call('EXPIRE', KEYS[5], ARGV[8])
redis.call('DEL', KEYS[4])
return {'COMPLETED', ARGV[3]}
"""

FAIL_SCRIPT = """
if redis.call('HGET', KEYS[1], 'user_id') ~= ARGV[1] then return 'NOT_FOUND' end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 'LEASE_LOST' end
if redis.call('HGET', KEYS[3], 'status') ~= 'PROCESSING' or
    redis.call('HGET', KEYS[3], 'token') ~= ARGV[2] then return 'STATE_CONFLICT' end
redis.call('HSET', KEYS[3], 'status', 'FAILED', 'error', ARGV[3])
redis.call('HDEL', KEYS[3], 'token')
redis.call('EXPIRE', KEYS[3], ARGV[4])
redis.call('DEL', KEYS[2])
return 'FAILED'
"""

RENEW_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] or
    redis.call('HGET', KEYS[2], 'status') ~= 'PROCESSING' then return 0 end
return redis.call('PEXPIRE', KEYS[1], ARGV[2])
"""


class RedisConversationRepository:
    def __init__(self, redis: Redis, config: ChatRedisConfig | None = None):
        self.redis = redis
        self.config = config or ChatRedisConfig.from_env()
        if self.config.lock_ttl_ms < 1 or self.config.result_ttl_seconds < 1:
            raise ValueError("Redis TTL settings must be positive")
        self.redis.ping()  # Fail loudly rather than falling back to process memory.

    @classmethod
    def from_config(cls, config: ChatRedisConfig | None = None) -> "RedisConversationRepository":
        settings = config or ChatRedisConfig.from_env()
        return cls(Redis.from_url(settings.url, decode_responses=True), settings)

    @staticmethod
    def _id(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("IDs must contain only letters, digits, underscore or hyphen")
        return value

    def _keys(self, user_id: str, conversation_id: str, request_id: str | None = None) -> tuple[str, ...]:
        uid, cid = self._id(user_id), self._id(conversation_id)
        prefix = f"chat:{{{uid}}}:c:{cid}"
        keys = (f"{prefix}:meta", f"{prefix}:messages", f"{prefix}:order", f"{prefix}:lock")
        if request_id is None:
            return keys
        return (*keys, f"chat:{{{uid}}}:req:{self._id(request_id)}", f"chat:{{{uid}}}:conversations")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _fingerprint(conversation_id: str, content: str) -> str:
        return hashlib.sha256(f"{conversation_id}\0{content}".encode("utf-8")).hexdigest()

    def create_conversation(self, user_id: str) -> Conversation:
        uid = self._id(user_id)
        cid = str(uuid4())
        now = self._now()
        meta = self._keys(uid, cid)[0]
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(meta, mapping={"user_id": uid, "created_at": now.isoformat(),
                                     "updated_at": now.isoformat(), "last_sequence": 0})
            pipe.zadd(f"chat:{{{uid}}}:conversations", {cid: now.timestamp()})
            pipe.execute()
        return Conversation(conversation_id=cid, user_id=uid, created_at=now, updated_at=now)

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        data = self.redis.hgetall(self._keys(user_id, conversation_id)[0])
        if not data or data.get("user_id") != user_id:
            raise ConversationNotFound(conversation_id)
        return Conversation(conversation_id=conversation_id, user_id=user_id,
                            created_at=datetime.fromisoformat(data["created_at"]),
                            updated_at=datetime.fromisoformat(data["updated_at"]))

    def list_conversations(self, user_id: str, offset: int = 0, limit: int = 20) -> list[Conversation]:
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid pagination")
        uid = self._id(user_id)
        ids = self.redis.zrevrange(f"chat:{{{uid}}}:conversations", offset, offset + limit - 1)
        result = []
        for cid in ids:
            try:
                result.append(self.get_conversation(uid, cid))
            except ConversationNotFound:
                continue
        return result

    def get_message(self, user_id: str, conversation_id: str, message_id: str) -> ChatMessage:
        self.get_conversation(user_id, conversation_id)
        raw = self.redis.hget(self._keys(user_id, conversation_id)[1], self._id(message_id))
        if raw is None:
            raise MessageNotFound(message_id)
        return ChatMessage.model_validate_json(raw)

    def list_messages(self, user_id: str, conversation_id: str, after_sequence: int = 0,
                      limit: int = 20) -> list[ChatMessage]:
        if after_sequence < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid pagination")
        self.get_conversation(user_id, conversation_id)
        _, messages_key, order_key, _ = self._keys(user_id, conversation_id)
        ids = self.redis.zrangebyscore(order_key, f"({after_sequence}", "+inf", start=0, num=limit)
        if not ids:
            return []
        values = self.redis.hmget(messages_key, ids)
        if any(value is None for value in values):
            raise RuntimeError("message index is inconsistent")
        return [ChatMessage.model_validate_json(value) for value in values]

    def get_turn(self, user_id: str, conversation_id: str, request_id: str) -> Turn | None:
        self.get_conversation(user_id, conversation_id)
        keys = self._keys(user_id, conversation_id, request_id)
        data = self.redis.hgetall(keys[4])
        if not data:
            return None
        if data.get("conversation_id") != conversation_id:
            raise RequestConflict(request_id)
        status = data["status"]
        if status == "PROCESSING" and self.redis.get(keys[3]) != data.get("token"):
            status = "UNKNOWN"
        return Turn(conversation_id=conversation_id, request_id=request_id, status=status,
                    user_message_id=data["user_message_id"],
                    assistant_message_id=data.get("assistant_message_id"), error=data.get("error"))

    def begin_turn(self, user_id: str, conversation_id: str, request_id: str, content: str) -> Turn:
        if not content.strip():
            raise ValueError("message content must not be empty")
        keys = self._keys(user_id, conversation_id, request_id)
        token, message_id = str(uuid4()), str(uuid4())
        now = self._now()
        message = ChatMessage(message_id=message_id, conversation_id=conversation_id,
                              user_id=user_id, request_id=request_id, role="user",
                              content=content, sequence=1, created_at=now)
        result = self.redis.eval(BEGIN_SCRIPT, len(keys), *keys, user_id,
                                 self._fingerprint(conversation_id, content), token,
                                 self.config.lock_ttl_ms, message_id, conversation_id,
                                 message.model_dump_json(), now.isoformat(), now.timestamp())
        status = result[0]
        if status == "NOT_FOUND":
            raise ConversationNotFound(conversation_id)
        if status == "CONFLICT":
            raise RequestConflict(request_id)
        if status == "BUSY":
            raise ConversationBusy(conversation_id)
        return Turn(conversation_id=conversation_id, request_id=request_id,
                    status="PROCESSING" if status == "PROCESSING_NEW" else status,
                    user_message_id=result[1],
                    assistant_message_id=result[2] or None if len(result) > 2 else None,
                    error=result[3] or None if len(result) > 3 else None,
                    lock_token=token if status == "PROCESSING_NEW" else None)

    def complete_turn(self, user_id: str, conversation_id: str, request_id: str,
                      lock_token: str, content: str) -> Turn:
        if not content.strip():
            raise ValueError("assistant content must not be empty")
        keys = self._keys(user_id, conversation_id, request_id)
        request = self.get_turn(user_id, conversation_id, request_id)
        if request is None:
            raise TurnStateConflict(request_id)
        message_id = str(uuid4())
        now = self._now()
        message = ChatMessage(message_id=message_id, conversation_id=conversation_id,
                              user_id=user_id, request_id=request_id, role="assistant",
                              content=content, sequence=1, created_at=now,
                              reply_to_message_id=request.user_message_id)
        result = self.redis.eval(COMPLETE_SCRIPT, len(keys), *keys, user_id, lock_token,
                                 message_id, message.model_dump_json(), now.isoformat(),
                                 now.timestamp(), conversation_id, self.config.result_ttl_seconds)
        if result[0] == "NOT_FOUND":
            raise ConversationNotFound(conversation_id)
        if result[0] == "LEASE_LOST":
            raise LeaseLost(conversation_id)
        if result[0] != "COMPLETED":
            raise TurnStateConflict(request_id)
        return Turn(conversation_id=conversation_id, request_id=request_id,
                    status=TurnStatus.COMPLETED, user_message_id=request.user_message_id,
                    assistant_message_id=result[1])

    def fail_turn(self, user_id: str, conversation_id: str, request_id: str,
                  lock_token: str, error: str) -> Turn:
        keys = self._keys(user_id, conversation_id, request_id)
        result = self.redis.eval(FAIL_SCRIPT, 3, keys[0], keys[3], keys[4], user_id,
                                 lock_token, error[:500], self.config.result_ttl_seconds)
        if result == "NOT_FOUND":
            raise ConversationNotFound(conversation_id)
        if result == "LEASE_LOST":
            raise LeaseLost(conversation_id)
        if result != "FAILED":
            raise TurnStateConflict(request_id)
        turn = self.get_turn(user_id, conversation_id, request_id)
        assert turn is not None
        return turn

    def renew_turn(self, user_id: str, conversation_id: str, request_id: str,
                   lock_token: str) -> None:
        keys = self._keys(user_id, conversation_id, request_id)
        if not self.redis.eval(RENEW_SCRIPT, 2, keys[3], keys[4],
                               lock_token, self.config.lock_ttl_ms):
            raise LeaseLost(conversation_id)
