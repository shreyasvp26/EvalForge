"""Provider catalog and BYOK connection schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_eval_application.use_cases.provider_connections import ProviderCatalogItemDTO
from agent_eval_domain.execution.provider_connection import ProviderConnection
from pydantic import BaseModel, ConfigDict, Field


class CreateProviderConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_key: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    display_name: str | None = None


class ProviderConnectionResponse(BaseModel):
    """Public connection identity — never includes secrets or ciphertext."""

    model_config = ConfigDict(extra="forbid")

    id: str
    provider_key: str
    credential_ref_id: str
    display_name: str
    status: str
    created_at: datetime | str
    masked_key: str
    key_fingerprint: str
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, connection: ProviderConnection) -> ProviderConnectionResponse:
        public = connection.to_public_dict()
        return cls(
            id=str(public["id"]),
            provider_key=str(public["provider_key"]),
            credential_ref_id=str(public["credential_ref_id"]),
            display_name=str(public["display_name"]),
            status=str(public["status"]),
            created_at=public["created_at"],  # type: ignore[arg-type]
            masked_key=str(public["masked_key"]),
            key_fingerprint=str(public["key_fingerprint"]),
            metadata=dict(public.get("metadata") or {}),  # type: ignore[arg-type]
        )


class ModelCatalogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    provider_key: str
    display_name: str
    adapter_keys: list[str]
    gateway_keys: list[str]
    notes: str = ""


class ProviderCatalogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_key: str
    display_name: str
    status: str
    supported_adapters: list[str]
    supported_gateways: list[str]
    notes: str
    configured: bool
    live_capable: bool
    models: list[dict[str, Any]]

    @classmethod
    def from_dto(cls, dto: ProviderCatalogItemDTO) -> ProviderCatalogItemResponse:
        return cls(
            provider_key=dto.provider_key,
            display_name=dto.display_name,
            status=dto.status,
            supported_adapters=list(dto.supported_adapters),
            supported_gateways=list(dto.supported_gateways),
            notes=dto.notes,
            configured=dto.configured,
            live_capable=dto.live_capable,
            models=[dict(m) for m in dto.models],
        )


class ConnectionModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    display_name: str
    in_catalog: bool
    adapter_keys: list[str]
    gateway_keys: list[str]


class VerifyProviderConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str
    provider_key: str
    status: str
    message: str
    checked_at: str
    models: list[ConnectionModelResponse]


class ConnectionModelsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str
    provider_key: str
    models: list[ConnectionModelResponse]
