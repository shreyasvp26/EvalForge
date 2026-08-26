"""Provider catalog and BYOK connection endpoints."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.use_cases.provider_connections import (
    CreateProviderConnectionCommand,
    ListProviderConnectionsQuery,
    RevokeProviderConnectionCommand,
    list_models_dto,
)
from fastapi import APIRouter, Query, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.provider import (
    CreateProviderConnectionRequest,
    ModelCatalogItemResponse,
    ProviderCatalogItemResponse,
    ProviderConnectionResponse,
)

router = APIRouter(tags=["providers"])


@router.get(
    "/v1/providers",
    response_model=CollectionResponse[ProviderCatalogItemResponse],
    summary="List providers",
    description=(
        "Static provider catalog with user configuration overlay. "
        "Only Google/gemini_cli is live-capable today."
    ),
)
def list_providers(
    actor: ActorDep,
    services: ServicesDep,
) -> CollectionResponse[ProviderCatalogItemResponse]:
    items = services.list_providers.execute(actor=actor)
    responses = [ProviderCatalogItemResponse.from_dto(item) for item in items]
    return CollectionResponse(
        items=responses,
        count=len(responses),
        next_cursor=None,
        has_more=False,
    )


@router.get(
    "/v1/models",
    response_model=CollectionResponse[ModelCatalogItemResponse],
    summary="List models",
)
def list_models(
    _actor: ActorDep,
    provider_key: Annotated[str | None, Query()] = None,
) -> CollectionResponse[ModelCatalogItemResponse]:
    raw = list_models_dto(provider_key)
    responses = [
        ModelCatalogItemResponse(
            model_id=str(row["model_id"]),
            provider_key=str(row["provider_key"]),
            display_name=str(row["display_name"]),
            adapter_keys=list(row["adapter_keys"]),  # type: ignore[arg-type]
            gateway_keys=list(row["gateway_keys"]),  # type: ignore[arg-type]
            notes=str(row.get("notes") or ""),
        )
        for row in raw
    ]
    return CollectionResponse(
        items=responses,
        count=len(responses),
        next_cursor=None,
        has_more=False,
    )


@router.get(
    "/v1/provider-connections",
    response_model=CollectionResponse[ProviderConnectionResponse],
    summary="List provider connections",
)
def list_provider_connections(
    actor: ActorDep,
    services: ServicesDep,
) -> CollectionResponse[ProviderConnectionResponse]:
    items = services.list_provider_connections.execute(
        ListProviderConnectionsQuery(actor=actor)
    )
    responses = [ProviderConnectionResponse.from_domain(c) for c in items]
    return CollectionResponse(
        items=responses,
        count=len(responses),
        next_cursor=None,
        has_more=False,
    )


@router.post(
    "/v1/provider-connections",
    response_model=ProviderConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create provider connection",
    description=(
        "Store an encrypted BYOK credential. The API key is never returned; "
        "responses include only a masked fingerprint."
    ),
)
def create_provider_connection(
    body: CreateProviderConnectionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> ProviderConnectionResponse:
    connection = services.create_provider_connection.execute(
        CreateProviderConnectionCommand(
            actor=actor,
            provider_key=body.provider_key,
            api_key=body.api_key,
            display_name=(body.display_name or "").strip(),
        )
    )
    return ProviderConnectionResponse.from_domain(connection)


@router.delete(
    "/v1/provider-connections/{connection_id}",
    response_model=ProviderConnectionResponse,
    summary="Revoke provider connection",
)
def revoke_provider_connection(
    connection_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> ProviderConnectionResponse:
    connection = services.revoke_provider_connection.execute(
        RevokeProviderConnectionCommand(actor=actor, connection_id=connection_id)
    )
    return ProviderConnectionResponse.from_domain(connection)
