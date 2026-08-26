"""Provider connection and model catalog use cases."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.execution.provider_connection import ProviderConnection
from agent_eval_domain.execution.provider_runtime import ProviderKey

from agent_eval_application.common.actor import Actor
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.model_catalog import (
    ProviderCapabilityStatus,
    get_provider_catalog_entry,
    list_models_for_provider,
    list_provider_catalog,
)
from agent_eval_application.ports.provider_connections import (
    CreateProviderConnectionInput,
    ProviderConnectionPort,
)
from agent_eval_application.use_cases.base import with_domain_errors


@dataclass(frozen=True, slots=True)
class CreateProviderConnectionCommand:
    actor: Actor
    provider_key: str
    api_key: str
    display_name: str = ""


@dataclass(frozen=True, slots=True)
class ListProviderConnectionsQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class RevokeProviderConnectionCommand:
    actor: Actor
    connection_id: str


class CreateProviderConnection:
    def __init__(self, store: ProviderConnectionPort) -> None:
        self._store = store

    def execute(self, command: CreateProviderConnectionCommand) -> ProviderConnection:
        provider_key = require_non_empty(command.provider_key, field="provider_key")
        api_key = require_non_empty(command.api_key, field="api_key")
        entry = get_provider_catalog_entry(provider_key)
        if entry is None or entry.status is ProviderCapabilityStatus.UNSUPPORTED:
            raise ApplicationValidationError(
                f"Provider {provider_key!r} is not available for BYOK connections",
                code="PROVIDER_UNSUPPORTED",
            )
        # Only Google is live-capable for coding agents; Anthropic/OmniRoute may
        # store credentials but are marked configurable in the catalog.
        return with_domain_errors(
            lambda: self._store.create(
                CreateProviderConnectionInput(
                    user_id=command.actor.id,
                    provider_key=provider_key,
                    api_key=api_key,
                    display_name=command.display_name.strip() or entry.display_name,
                )
            )
        )


class ListProviderConnections:
    def __init__(self, store: ProviderConnectionPort) -> None:
        self._store = store

    def execute(self, query: ListProviderConnectionsQuery) -> list[ProviderConnection]:
        return self._store.list_for_user(query.actor.id)


class RevokeProviderConnection:
    def __init__(self, store: ProviderConnectionPort) -> None:
        self._store = store

    def execute(self, command: RevokeProviderConnectionCommand) -> ProviderConnection:
        connection_id = require_non_empty(command.connection_id, field="connection_id")
        return with_domain_errors(
            lambda: self._store.revoke_for_user(
                user_id=command.actor.id, connection_id=connection_id
            )
        )


@dataclass(frozen=True, slots=True)
class ProviderCatalogItemDTO:
    provider_key: str
    display_name: str
    status: str
    supported_adapters: tuple[str, ...]
    supported_gateways: tuple[str, ...]
    notes: str
    configured: bool
    live_capable: bool
    models: tuple[dict[str, object], ...]


class ListProviders:
    """Catalog of providers with optional user configuration overlay."""

    def __init__(self, store: ProviderConnectionPort | None = None) -> None:
        self._store = store

    def execute(self, *, actor: Actor | None = None) -> list[ProviderCatalogItemDTO]:
        configured_providers: set[str] = set()
        if actor is not None and self._store is not None:
            for connection in self._store.list_for_user(actor.id):
                if connection.is_usable:
                    configured_providers.add(connection.provider_key.value)

        items: list[ProviderCatalogItemDTO] = []
        for entry in list_provider_catalog():
            models = [
                {
                    "model_id": model.model_id,
                    "display_name": model.display_name,
                    "adapter_keys": sorted(model.adapter_keys),
                    "gateway_keys": sorted(g.value for g in model.gateway_keys),
                }
                for model in entry.models
            ]
            items.append(
                ProviderCatalogItemDTO(
                    provider_key=entry.provider_key.value,
                    display_name=entry.display_name,
                    status=entry.status.value,
                    supported_adapters=tuple(sorted(entry.supported_adapters)),
                    supported_gateways=tuple(
                        sorted(g.value for g in entry.supported_gateways)
                    ),
                    notes=entry.notes,
                    configured=entry.provider_key.value in configured_providers,
                    live_capable=entry.status is ProviderCapabilityStatus.LIVE_CAPABLE,
                    models=tuple(models),
                )
            )
        return items


def list_models_dto(provider_key: str | None = None) -> list[dict[str, object]]:
    if provider_key:
        models = list_models_for_provider(provider_key)
    else:
        models = tuple(
            model for entry in list_provider_catalog() for model in entry.models
        )
    return [
        {
            "model_id": model.model_id,
            "provider_key": model.provider_key.value,
            "display_name": model.display_name,
            "adapter_keys": sorted(model.adapter_keys),
            "gateway_keys": sorted(g.value for g in model.gateway_keys),
            "notes": model.notes,
        }
        for model in models
    ]


# Silence unused import warning for re-exports in tests
_ = ProviderKey
