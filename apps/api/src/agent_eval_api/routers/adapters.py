"""Adapter endpoints — invoke Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    PublishAdapterVersionCommand,
)
from fastapi import APIRouter, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.agent import (
    AdapterResponse,
    AdapterVersionResponse,
    CreateAdapterDraftVersionRequest,
    CreateAdapterRequest,
)

router = APIRouter(prefix="/v1/adapters", tags=["adapters"])


@router.post("", response_model=AdapterResponse, status_code=status.HTTP_201_CREATED)
def create_adapter(
    body: CreateAdapterRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AdapterResponse:
    dto = services.create_adapter.execute(
        CreateAdapterCommand(
            actor=actor,
            agent_id=body.agent_id,
            name=body.name,
            idempotency_key=idempotency_key,
        )
    )
    return AdapterResponse.from_dto(dto)


@router.post(
    "/{adapter_id}/versions",
    response_model=AdapterVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_adapter_draft_version(
    adapter_id: str,
    body: CreateAdapterDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> AdapterVersionResponse:
    dto = services.create_adapter_draft_version.execute(
        CreateAdapterDraftVersionCommand(
            actor=actor,
            adapter_id=adapter_id,
            label=body.label,
            notes=body.notes,
        )
    )
    return AdapterVersionResponse.from_dto(dto)


@router.post(
    "/{adapter_id}/versions/{version_id}/publish",
    response_model=AdapterVersionResponse,
)
def publish_adapter_version(
    adapter_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> AdapterVersionResponse:
    dto = services.publish_adapter_version.execute(
        PublishAdapterVersionCommand(
            actor=actor, adapter_id=adapter_id, version_id=version_id
        )
    )
    return AdapterVersionResponse.from_dto(dto)
