"""System info endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from agent_eval_api import __version__
from agent_eval_api.dependencies import ActorDep, SettingsDep
from agent_eval_api.schemas.health import SystemInfoResponse

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
def system_info(_actor: ActorDep, settings: SettingsDep) -> SystemInfoResponse:
    """Authenticated process metadata for clients and operators."""
    return SystemInfoResponse(
        service="evalforge-control-plane",
        version=__version__,
        api_version="v1",
        environment=settings.environment,
    )
