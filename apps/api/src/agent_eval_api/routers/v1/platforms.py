"""Platform catalog endpoints."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.commands.platform import (
    CreatePlatformCommand,
    CreatePlatformDraftVersionCommand,
    PublishPlatformVersionCommand,
)
from agent_eval_application.queries.queries import GetPlatformQuery, ListPlatformsQuery
from fastapi import APIRouter, Depends, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.platform import (
    CreatePlatformDraftVersionRequest,
    CreatePlatformRequest,
    PlatformResponse,
    PlatformVersionResponse,
)

router = APIRouter(prefix="/v1/platforms", tags=["platforms"])


@router.post("", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
def create_platform(
    body: CreatePlatformRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlatformResponse:
    return PlatformResponse.from_dto(
        services.create_platform.execute(
            CreatePlatformCommand(
                actor=actor,
                name=body.name,
                idempotency_key=idempotency_key,
            )
        )
    )


@router.get("", response_model=CollectionResponse[PlatformResponse])
def list_platforms(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[PlatformResponse]:
    items = services.list_platforms.execute(ListPlatformsQuery(actor=actor))
    return params.apply([PlatformResponse.from_dto(item) for item in items])


@router.get("/{platform_id}", response_model=PlatformResponse)
def get_platform(
    platform_id: str, actor: ActorDep, services: ServicesDep
) -> PlatformResponse:
    return PlatformResponse.from_dto(
        services.get_platform.execute(
            GetPlatformQuery(actor=actor, platform_id=platform_id)
        )
    )


@router.post(
    "/{platform_id}/versions",
    response_model=PlatformVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_draft_version(
    platform_id: str,
    body: CreatePlatformDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> PlatformVersionResponse:
    return PlatformVersionResponse.from_dto(
        services.create_platform_draft_version.execute(
            CreatePlatformDraftVersionCommand(
                actor=actor,
                platform_id=platform_id,
                label=body.label,
                sandbox_policy=body.sandbox_policy,
                execution_policy=body.execution_policy,
                timeout_policy=body.timeout_policy,
                environment_policy=body.environment_policy,
                grading_policy=body.grading_policy,
                notes=body.notes,
            )
        )
    )


@router.post(
    "/{platform_id}/versions/{version_id}/publish",
    response_model=PlatformVersionResponse,
)
def publish_platform_version(
    platform_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> PlatformVersionResponse:
    return PlatformVersionResponse.from_dto(
        services.publish_platform_version.execute(
            PublishPlatformVersionCommand(
                actor=actor,
                platform_id=platform_id,
                version_id=version_id,
            )
        )
    )
