"""API router registration."""

from fastapi import APIRouter
from .auth import router as auth_router
from .conversations import router as conversations_router
from .health import router as health_router
from .workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(health_router)

__all__ = ["api_router"]
