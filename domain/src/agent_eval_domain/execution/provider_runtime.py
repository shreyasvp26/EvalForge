"""Provider, gateway, model, and routing identity for coding-agent execution.

These value objects describe *how inference was reached* for a Run.
They never carry secrets. Agent / Adapter / Platform remain separate aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_domain.common.errors import InvariantViolation

# Sentinel / reserved model tokens that must not be treated as exact model pins.
AUTO_MODEL_TOKEN = "auto"
"""Experimental auto-routing request token (never a canonical model id)."""


class ProviderKey(StrEnum):
    """Upstream inference vendor or multi-vendor gateway identity."""

    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OMNIROUTE = "omniroute"


class GatewayKey(StrEnum):
    """How EvalForge reaches a provider for coding-agent inference."""

    DIRECT = "direct"
    """Adapter talks to the vendor (e.g. Gemini CLI + GEMINI_API_KEY)."""

    OMNIROUTE = "omniroute"
    """Optional OpenAI-compatible multi-provider gateway."""


class RoutingMode(StrEnum):
    """Whether model selection is pinned or delegated to the gateway."""

    FIXED = "fixed"
    """Exact model requested — required for canonical benchmark results."""

    AUTO = "auto"
    """Gateway may choose a model — experimental / non-canonical only."""


def parse_provider_key(raw: str) -> ProviderKey:
    cleaned = str(raw).strip().lower()
    try:
        return ProviderKey(cleaned)
    except ValueError as exc:
        known = ", ".join(sorted(p.value for p in ProviderKey))
        raise InvariantViolation(
            f"Unknown provider_key {raw!r}; expected one of: {known}",
            code="UNKNOWN_PROVIDER_KEY",
            details={"provider_key": raw},
        ) from exc


def parse_gateway_key(raw: str) -> GatewayKey:
    cleaned = str(raw).strip().lower()
    try:
        return GatewayKey(cleaned)
    except ValueError as exc:
        known = ", ".join(sorted(g.value for g in GatewayKey))
        raise InvariantViolation(
            f"Unknown gateway_key {raw!r}; expected one of: {known}",
            code="UNKNOWN_GATEWAY_KEY",
            details={"gateway_key": raw},
        ) from exc


def parse_routing_mode(raw: str) -> RoutingMode:
    cleaned = str(raw).strip().lower()
    try:
        return RoutingMode(cleaned)
    except ValueError as exc:
        raise InvariantViolation(
            f"Unknown routing_mode {raw!r}; expected 'fixed' or 'auto'",
            code="UNKNOWN_ROUTING_MODE",
            details={"routing_mode": raw},
        ) from exc


@dataclass(frozen=True, slots=True)
class ModelId:
    """Exact model identifier (never a secret, never silently rewritten)."""

    value: str

    def __post_init__(self) -> None:
        cleaned = str(self.value).strip()
        if not cleaned:
            raise InvariantViolation(
                "model_id must be non-empty",
                code="EMPTY_MODEL_ID",
            )
        object.__setattr__(self, "value", cleaned)

    def is_auto_token(self) -> bool:
        return self.value.lower() == AUTO_MODEL_TOKEN


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Requested vs observed model identity for a single execution."""

    requested_model: str | None
    actual_model: str | None
    routing_mode: RoutingMode

    def __post_init__(self) -> None:
        if not isinstance(self.routing_mode, RoutingMode):
            raise InvariantViolation(
                "routing_mode must be a RoutingMode",
                code="INVALID_ROUTING_MODE",
            )
        requested = (
            str(self.requested_model).strip()
            if self.requested_model is not None
            else None
        )
        actual = (
            str(self.actual_model).strip() if self.actual_model is not None else None
        )
        if requested == "":
            requested = None
        if actual == "":
            actual = None
        object.__setattr__(self, "requested_model", requested)
        object.__setattr__(self, "actual_model", actual)

        if self.routing_mode is RoutingMode.FIXED:
            if requested is None:
                raise InvariantViolation(
                    "fixed routing requires an explicit requested_model",
                    code="FIXED_ROUTING_REQUIRES_MODEL",
                )
            if requested.lower() == AUTO_MODEL_TOKEN:
                raise InvariantViolation(
                    "fixed routing cannot use model 'auto'; use routing_mode=auto "
                    "for experimental routing (non-canonical)",
                    code="FIXED_ROUTING_REJECTS_AUTO",
                )

        if self.routing_mode is RoutingMode.AUTO:
            if requested is not None and requested.lower() != AUTO_MODEL_TOKEN:
                # Auto mode may still record a preference, but the token must be
                # explicit about non-canonical routing via routing_mode itself.
                pass

    @property
    def is_canonical(self) -> bool:
        """Canonical benchmark results require fixed routing + exact model pin."""
        return (
            self.routing_mode is RoutingMode.FIXED
            and self.requested_model is not None
            and self.requested_model.lower() != AUTO_MODEL_TOKEN
        )


@dataclass(frozen=True, slots=True)
class ProviderRuntimeIdentity:
    """Non-secret provider/gateway/model identity attached to a Run."""

    provider_key: ProviderKey
    gateway_key: GatewayKey
    model: ModelIdentity
    credential_ref_id: str | None = None
    fallback_used: bool | None = None
    """True/False when known; None when the provider does not report fallback."""

    def __post_init__(self) -> None:
        if not isinstance(self.provider_key, ProviderKey):
            raise InvariantViolation(
                "provider_key must be a ProviderKey",
                code="INVALID_PROVIDER_KEY",
            )
        if not isinstance(self.gateway_key, GatewayKey):
            raise InvariantViolation(
                "gateway_key must be a GatewayKey",
                code="INVALID_GATEWAY_KEY",
            )
        if not isinstance(self.model, ModelIdentity):
            raise InvariantViolation(
                "model must be a ModelIdentity",
                code="INVALID_MODEL_IDENTITY",
            )
        ref = self.credential_ref_id
        if ref is not None:
            cleaned = str(ref).strip()
            if not cleaned:
                cleaned = None
            object.__setattr__(self, "credential_ref_id", cleaned)

        # OmniRoute gateway implies omniroute provider identity for routing layer.
        if (
            self.gateway_key is GatewayKey.OMNIROUTE
            and self.provider_key is not ProviderKey.OMNIROUTE
        ):
            # Allowed: gateway=omniroute can still record the *upstream* vendor
            # when known (e.g. google behind OmniRoute). No hard reject.
            pass

        if (
            self.gateway_key is GatewayKey.DIRECT
            and self.provider_key is ProviderKey.OMNIROUTE
        ):
            raise InvariantViolation(
                "provider omniroute requires gateway_key=omniroute",
                code="OMNIROUTE_REQUIRES_GATEWAY",
            )

    @property
    def is_canonical_evaluation(self) -> bool:
        if self.fallback_used is True:
            return False
        return self.model.is_canonical

    def to_execution_metadata(self) -> dict[str, str]:
        """Serialize into allowlisted execution_metadata (no secrets)."""
        meta: dict[str, str] = {
            "provider_key": self.provider_key.value,
            "gateway_key": self.gateway_key.value,
            "routing_mode": self.model.routing_mode.value,
            "canonical_evaluation": "true" if self.is_canonical_evaluation else "false",
        }
        if self.model.requested_model is not None:
            meta["requested_model"] = self.model.requested_model
        if self.model.actual_model is not None:
            meta["actual_model"] = self.model.actual_model
        if self.credential_ref_id is not None:
            meta["credential_ref_id"] = self.credential_ref_id
        if self.fallback_used is not None:
            meta["fallback_used"] = "true" if self.fallback_used else "false"
        return meta


def provider_runtime_from_metadata(
    metadata: dict[str, str] | None,
) -> ProviderRuntimeIdentity | None:
    """Reconstruct provider runtime identity from persisted execution_metadata."""
    if not metadata:
        return None
    provider_raw = metadata.get("provider_key")
    gateway_raw = metadata.get("gateway_key")
    routing_raw = metadata.get("routing_mode")
    if not provider_raw or not gateway_raw or not routing_raw:
        return None

    fallback_raw = metadata.get("fallback_used")
    fallback: bool | None
    if fallback_raw is None:
        fallback = None
    else:
        fallback = fallback_raw.strip().lower() in {"1", "true", "yes"}

    return ProviderRuntimeIdentity(
        provider_key=parse_provider_key(provider_raw),
        gateway_key=parse_gateway_key(gateway_raw),
        model=ModelIdentity(
            requested_model=metadata.get("requested_model"),
            actual_model=metadata.get("actual_model"),
            routing_mode=parse_routing_mode(routing_raw),
        ),
        credential_ref_id=metadata.get("credential_ref_id"),
        fallback_used=fallback,
    )
