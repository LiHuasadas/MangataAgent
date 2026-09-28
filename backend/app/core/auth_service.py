"""User Authentication Service with Redis Storage.

Provides secure password hashing with PBKDF2-HMAC-SHA256, user registration,
login authentication, and session token lifecycle management.
"""

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from redis import Redis


class AuthError(Exception):
    """Base exception for authentication and registration failures."""
    pass


class UserAlreadyExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class UserNotFoundError(AuthError):
    pass


class AuthService:
    """Authentication and user management backed by Redis."""

    SESSION_TTL_SECONDS = 7 * 86400  # 7 days
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]{3,32}$')

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Generate a secure PBKDF2-HMAC-SHA256 password hash and salt."""
        if not salt:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000,
        ).hex()
        return pwd_hash, salt

    def register(self, username: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user and issue an initial session token."""
        username = username.strip().lower()
        if not self.USERNAME_PATTERN.match(username):
            raise AuthError("用户名必须为 3-32 位字母、数字、下划线、中划线或点号")
        if len(password) < 6:
            raise AuthError("密码长度不能少于 6 位")

        username_key = f"user:by_username:{username}"
        # Atomically check if username already taken
        user_id = f"user_{secrets.token_hex(8)}"
        success = self.redis.set(username_key, user_id, nx=True)
        if not success:
            raise UserAlreadyExistsError(f"用户名 '{username}' 已被注册")

        pwd_hash, salt = self._hash_password(password)
        now_iso = datetime.now(timezone.utc).isoformat()

        user_data = {
            "user_id": user_id,
            "username": username,
            "display_name": display_name or username,
            "password_hash": pwd_hash,
            "salt": salt,
            "created_at": now_iso,
        }

        # Store user profile in Redis
        profile_key = f"user:profile:{user_id}"
        self.redis.set(profile_key, json.dumps(user_data))

        # Create session token
        token = self._create_session(user_id)

        return {
            "user_id": user_id,
            "username": username,
            "display_name": user_data["display_name"],
            "token": token,
            "created_at": now_iso,
        }

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with username and password, returns session token."""
        username = username.strip().lower()
        username_key = f"user:by_username:{username}"
        user_id = self.redis.get(username_key)
        if not user_id:
            raise InvalidCredentialsError("用户名或密码错误")

        profile_key = f"user:profile:{user_id}"
        raw_profile = self.redis.get(profile_key)
        if not raw_profile:
            raise InvalidCredentialsError("用户名或密码错误")

        user_data = json.loads(raw_profile)
        expected_hash = user_data["password_hash"]
        salt = user_data["salt"]

        calc_hash, _ = self._hash_password(password, salt=salt)
        if not secrets.compare_digest(calc_hash, expected_hash):
            raise InvalidCredentialsError("用户名或密码错误")

        token = self._create_session(user_id)

        return {
            "user_id": user_id,
            "username": user_data["username"],
            "display_name": user_data.get("display_name", user_data["username"]),
            "token": token,
            "created_at": user_data.get("created_at"),
        }

    def _create_session(self, user_id: str) -> str:
        """Create a session token and store in Redis with TTL."""
        token = f"mgt_{secrets.token_urlsafe(32)}"
        session_key = f"user:session:{token}"
        self.redis.set(session_key, user_id, ex=self.SESSION_TTL_SECONDS)

        # Track session under user's active session set
        user_sessions_key = f"user:sessions_of:{user_id}"
        self.redis.sadd(user_sessions_key, token)
        self.redis.expire(user_sessions_key, self.SESSION_TTL_SECONDS)
        return token

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user profile."""
        if not token:
            return None
        session_key = f"user:session:{token}"
        user_id = self.redis.get(session_key)
        if not user_id:
            return None

        profile_key = f"user:profile:{user_id}"
        raw_profile = self.redis.get(profile_key)
        if not raw_profile:
            return None

        data = json.loads(raw_profile)
        return {
            "user_id": data["user_id"],
            "username": data["username"],
            "display_name": data.get("display_name", data["username"]),
            "created_at": data.get("created_at"),
        }

    def logout(self, token: str) -> bool:
        """Invalidate session token."""
        if not token:
            return False
        session_key = f"user:session:{token}"
        user_id = self.redis.get(session_key)
        if user_id:
            user_sessions_key = f"user:sessions_of:{user_id}"
            self.redis.srem(user_sessions_key, token)
        deleted = self.redis.delete(session_key)
        return bool(deleted)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile by user_id."""
        profile_key = f"user:profile:{user_id}"
        raw_profile = self.redis.get(profile_key)
        if not raw_profile:
            return None
        data = json.loads(raw_profile)
        return {
            "user_id": data["user_id"],
            "username": data["username"],
            "display_name": data.get("display_name", data["username"]),
            "created_at": data.get("created_at"),
        }
