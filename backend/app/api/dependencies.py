"""Dependencies for the FastAPI API layer."""

import json
import os
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..chat.service import ChatService
from ..agents.host_agent import HostAgent

bearer_scheme = HTTPBearer(auto_error=False)


def get_redis_client(request: Request):
    """Retrieve Redis client from app.state or fallback to from_env()."""
    from redis import Redis
    from ..chat.config import ChatRedisConfig
    client = getattr(request.app.state, "redis", None)
    if not client:
        config = ChatRedisConfig.from_env()
        client = Redis.from_url(config.url, decode_responses=True)
        if hasattr(request.app, "state"):
            request.app.state.redis = client
    return client


def get_auth_service(request: Request):
    """Retrieve AuthService instance backed by Redis."""
    from ..core.auth_service import AuthService
    service = getattr(request.app.state, "auth_service", None)
    if not service:
        redis_client = get_redis_client(request)
        service = AuthService(redis_client)
        if hasattr(request.app, "state"):
            request.app.state.auth_service = service
    return service


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """Extract and validate user ID from Bearer token, Redis session, or development headers."""
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    
    if not token:
        token = request.headers.get("X-API-Key") or request.query_params.get("token")
        
    api_keys_env = os.getenv("CHAT_API_KEYS")
    if api_keys_env:
        try:
            api_keys: dict[str, str] = json.loads(api_keys_env)
            if token and token in api_keys:
                return api_keys[token]
        except Exception:
            pass

    # Check if token is a valid Redis session token
    if token:
        try:
            auth_service = get_auth_service(request)
            user_data = auth_service.get_user_by_token(token)
            if user_data:
                return user_data["user_id"]
        except Exception:
            pass

    dev_user_id = request.headers.get("X-User-ID")
    if dev_user_id:
        return dev_user_id

    if token:
        return f"user_{token[:8]}"

    default_user = os.getenv("DEFAULT_USER_ID", "default_user")
    return default_user



def get_chat_service(request: Request) -> ChatService:
    service: Optional[ChatService] = getattr(request.app.state, "chat_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="ChatService is not initialized")
    return service


def get_host_agent(request: Request) -> HostAgent:
    agent: Optional[HostAgent] = getattr(request.app.state, "host_agent", None)
    if not agent:
        raise HTTPException(status_code=500, detail="HostAgent is not initialized")
    return agent


def get_workspace_service(request: Request):
    """Retrieve WorkspaceService from app.state or fallback to default instance."""
    from ..core.workspace_service import WorkspaceService
    service = getattr(request.app.state, "workspace_service", None)
    if not service:
        service = WorkspaceService()
        if hasattr(request.app, "state"):
            request.app.state.workspace_service = service
    return service

