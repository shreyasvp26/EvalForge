"""Adapter endpoints — invoke Application use cases only."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    PublishAdapterVersionCommand,
)
from agent_eval_application.queries.queries import GetAdapterQuery, ListAdaptersQuery
from fastapi import APIRouter, Depends, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.agent import (
    AdapterResponse,
    AdapterVersionResponse,
    CreateAdapterDraftVersionRequest,
    CreateAdapterRequest,
)
from agent_eval_api.schemas.common import CollectionResponse

router = APIRouter(prefix="/v1/adapters", tags=["adapters"])


@router.post(
    "",
    response_model=AdapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Adapter",
)
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


@router.get(
    "",
    response_model=CollectionResponse[AdapterResponse],
    summary="List Adapters",
)
def list_adapters(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[AdapterResponse]:
    items = services.list_adapters.execute(ListAdaptersQuery(actor=actor))
    responses = [AdapterResponse.from_dto(a) for a in items]
    return params.apply(responses)


@router.get(
    "/{adapter_id}",
    response_model=AdapterResponse,
    summary="Get Adapter",
)
def get_adapter(
    adapter_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> AdapterResponse:
    dto = services.get_adapter.execute(
        GetAdapterQuery(actor=actor, adapter_id=adapter_id)
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
