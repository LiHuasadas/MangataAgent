"""Healthcheck endpoint."""

from fastapi import APIRouter, Request
from .schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request):
    redis_ok = False
    try:
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client and redis_client.ping():
            redis_ok = True
    except Exception:
        redis_ok = False

    agent_ok = getattr(request.app.state, "host_agent", None) is not None

    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis=redis_ok,
        agent_ready=agent_ok,
        version="1.0.0",
    )
