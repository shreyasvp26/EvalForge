"""Health endpoints — operational liveness / readiness (System Overview §12).

Unauthenticated by design so orchestrators can probe without credentials.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from agent_eval_api.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Process is up."""
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=ReadyResponse)
def readiness(request: Request) -> ReadyResponse:
    """Process can accept traffic (composition root present; deps reachable)."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        return ReadyResponse(
            status="not_ready",
            checks={"composition": "missing"},
        )

    checks = container.readiness_checks()
    status = "ok" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)
