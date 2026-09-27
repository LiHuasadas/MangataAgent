"""Redis settings for conversation storage."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatRedisConfig:
    url: str = "redis://localhost:6378/0"
    lock_ttl_ms: int = 30_000
    result_ttl_seconds: int = 86_400

    @classmethod
    def from_env(cls) -> "ChatRedisConfig":
        return cls(
            url=os.getenv("CHAT_REDIS_URL", cls.url),
            lock_ttl_ms=int(os.getenv("CHAT_LOCK_TTL_MS", cls.lock_ttl_ms)),
            result_ttl_seconds=int(os.getenv("CHAT_RESULT_TTL_SECONDS", cls.result_ttl_seconds)),
        )
