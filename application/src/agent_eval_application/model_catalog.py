"""Static provider + model catalog for Phase 13 UI/validation.

Honest support status only. Do not advertise live capability that is not
wired into the worker adapter registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_domain.execution.provider_runtime import GatewayKey, ProviderKey


class ProviderCapabilityStatus(StrEnum):
    LIVE_CAPABLE = "live_capable"
    """Supported for live coding-agent execution today."""

    CONFIGURABLE = "configurable"
    """Credential can be stored; live adapter path not verified."""

    UNSUPPORTED = "unsupported"
    """Recognized enum only — not selectable for runs."""


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    model_id: str
    provider_key: ProviderKey
    display_name: str
    adapter_keys: frozenset[str]
    gateway_keys: frozenset[GatewayKey]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProviderCatalogEntry:
    provider_key: ProviderKey
    display_name: str
    status: ProviderCapabilityStatus
    supported_adapters: frozenset[str]
    supported_gateways: frozenset[GatewayKey]
    models: tuple[ModelCatalogEntry, ...]
    notes: str = ""


PROVIDER_CATALOG: dict[str, ProviderCatalogEntry] = {
    ProviderKey.GOOGLE.value: ProviderCatalogEntry(
        provider_key=ProviderKey.GOOGLE,
        display_name="Google",
        status=ProviderCapabilityStatus.LIVE_CAPABLE,
        supported_adapters=frozenset({"gemini_cli"}),
        supported_gateways=frozenset({GatewayKey.DIRECT}),
        models=(
            ModelCatalogEntry(
                model_id="gemini-2.0-flash",
                provider_key=ProviderKey.GOOGLE,
                display_name="Gemini 2.0 Flash",
                adapter_keys=frozenset({"gemini_cli"}),
                gateway_keys=frozenset({GatewayKey.DIRECT}),
            ),
            ModelCatalogEntry(
                model_id="gemini-2.5-flash",
                provider_key=ProviderKey.GOOGLE,
                display_name="Gemini 2.5 Flash",
                adapter_keys=frozenset({"gemini_cli"}),
                gateway_keys=frozenset({GatewayKey.DIRECT}),
            ),
            ModelCatalogEntry(
                model_id="gemini-2.5-pro",
                provider_key=ProviderKey.GOOGLE,
                display_name="Gemini 2.5 Pro",
                adapter_keys=frozenset({"gemini_cli"}),
                gateway_keys=frozenset({GatewayKey.DIRECT}),
            ),
        ),
        notes=(
            "Live via gemini_cli + direct gateway. "
            "Exact --model pinning required for canonical runs."
        ),
    ),
    ProviderKey.ANTHROPIC.value: ProviderCatalogEntry(
        provider_key=ProviderKey.ANTHROPIC,
        display_name="Anthropic",
        status=ProviderCapabilityStatus.CONFIGURABLE,
        supported_adapters=frozenset({"claude_code"}),
        supported_gateways=frozenset({GatewayKey.DIRECT}),
        models=(),
        notes="Credentials may be stored; live Claude Code is not production-verified.",
    ),
    ProviderKey.OPENAI.value: ProviderCatalogEntry(
        provider_key=ProviderKey.OPENAI,
        display_name="OpenAI",
        status=ProviderCapabilityStatus.UNSUPPORTED,
        supported_adapters=frozenset(),
        supported_gateways=frozenset({GatewayKey.DIRECT, GatewayKey.OMNIROUTE}),
        models=(),
        notes="Enum recognized; no live coding-agent adapter registered.",
    ),
    ProviderKey.OMNIROUTE.value: ProviderCatalogEntry(
        provider_key=ProviderKey.OMNIROUTE,
        display_name="OmniRoute",
        status=ProviderCapabilityStatus.CONFIGURABLE,
        supported_adapters=frozenset(),
        supported_gateways=frozenset({GatewayKey.OMNIROUTE}),
        models=(),
        notes=(
            "Optional gateway only. Not the evaluation engine. "
            "Live integration gated."
        ),
    ),
}


def list_provider_catalog() -> tuple[ProviderCatalogEntry, ...]:
    return tuple(PROVIDER_CATALOG[key] for key in sorted(PROVIDER_CATALOG))


def get_provider_catalog_entry(provider_key: str) -> ProviderCatalogEntry | None:
    return PROVIDER_CATALOG.get(provider_key.strip().lower())


def list_models_for_provider(provider_key: str) -> tuple[ModelCatalogEntry, ...]:
    entry = get_provider_catalog_entry(provider_key)
    if entry is None:
        return ()
    return entry.models


def find_model(model_id: str) -> ModelCatalogEntry | None:
    needle = model_id.strip()
    for provider in PROVIDER_CATALOG.values():
        for model in provider.models:
            if model.model_id == needle:
                return model
    return None


def validate_model_for_adapter(
    *,
    model_id: str,
    adapter_key: str,
    provider_key: str,
    gateway_key: str,
) -> ModelCatalogEntry:
    from agent_eval_application.provider_runtime import UnsupportedProviderModelError

    model = find_model(model_id)
    if model is None:
        raise UnsupportedProviderModelError(
            f"Unknown or unsupported model {model_id!r}",
            details={"model_id": model_id},
        )
    if model.provider_key.value != provider_key.strip().lower():
        raise UnsupportedProviderModelError(
            f"Model {model_id!r} belongs to provider {model.provider_key.value}, "
            f"not {provider_key!r}",
            details={
                "model_id": model_id,
                "provider_key": provider_key,
            },
        )
    if adapter_key not in model.adapter_keys:
        raise UnsupportedProviderModelError(
            f"Model {model_id!r} is not supported by adapter {adapter_key!r}",
            details={"model_id": model_id, "adapter_key": adapter_key},
        )
    from agent_eval_domain.execution.provider_runtime import parse_gateway_key

    gateway = parse_gateway_key(gateway_key)
    if gateway not in model.gateway_keys:
        raise UnsupportedProviderModelError(
            f"Model {model_id!r} is not supported via gateway {gateway.value}",
            details={"model_id": model_id, "gateway_key": gateway.value},
        )
    return model
