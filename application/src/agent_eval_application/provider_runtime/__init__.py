"""Application helpers for coding-agent provider / model runtime resolution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.credentials import (
    CredentialBackend,
    CredentialReference,
)
from agent_eval_domain.execution.provider_runtime import (
    AUTO_MODEL_TOKEN,
    GatewayKey,
    ModelId,
    ModelIdentity,
    ProviderKey,
    ProviderRuntimeIdentity,
    RoutingMode,
    parse_gateway_key,
    parse_provider_key,
    parse_routing_mode,
)

from agent_eval_application.adapter_capabilities import get_adapter_capability

# Default credential reference ids for operator-managed env secrets.
# These are identities, not secrets — safe to persist in provenance.
DEFAULT_ENV_CREDENTIAL_REFS: dict[str, CredentialReference] = {
    "env:GEMINI_API_KEY": CredentialReference(
        id="env:GEMINI_API_KEY",
        provider_key=ProviderKey.GOOGLE,
        label="Operator Gemini API key",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="GEMINI_API_KEY",
    ),
    "env:GOOGLE_API_KEY": CredentialReference(
        id="env:GOOGLE_API_KEY",
        provider_key=ProviderKey.GOOGLE,
        label="Operator Google API key (Gemini alias)",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="GOOGLE_API_KEY",
    ),
    "env:OPENAI_API_KEY": CredentialReference(
        id="env:OPENAI_API_KEY",
        provider_key=ProviderKey.OPENAI,
        label="Operator OpenAI API key",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="OPENAI_API_KEY",
    ),
    "env:ANTHROPIC_API_KEY": CredentialReference(
        id="env:ANTHROPIC_API_KEY",
        provider_key=ProviderKey.ANTHROPIC,
        label="Operator Anthropic API key",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="ANTHROPIC_API_KEY",
    ),
    "env:GROQ_API_KEY": CredentialReference(
        id="env:GROQ_API_KEY",
        provider_key=ProviderKey.GROQ,
        label="Operator Groq API key",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="GROQ_API_KEY",
    ),
    "env:OMNIROUTE_API_KEY": CredentialReference(
        id="env:OMNIROUTE_API_KEY",
        provider_key=ProviderKey.OMNIROUTE,
        label="Operator OmniRoute API key",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="OMNIROUTE_API_KEY",
    ),
}

# Adapter key → default direct provider when gateway=direct.
_ADAPTER_DEFAULT_PROVIDER: dict[str, ProviderKey] = {
    "gemini_cli": ProviderKey.GOOGLE,
    "claude_code": ProviderKey.ANTHROPIC,
    "codex": ProviderKey.OPENAI,
    "cursor": ProviderKey.ANTHROPIC,
    "aider": ProviderKey.OPENAI,
}


@dataclass(frozen=True, slots=True)
class ProviderRuntimeRequest:
    """Caller-supplied (or env-derived) runtime selection for one execution."""

    adapter_key: str
    provider_key: str | None = None
    gateway_key: str | None = None
    model_id: str | None = None
    routing_mode: str | None = None
    credential_ref_id: str | None = None
    actual_model: str | None = None
    fallback_used: bool | None = None
    allow_auto_routing: bool = False
    """If False, routing_mode=auto / model=auto is rejected (canonical path)."""


class UnsupportedProviderModelError(InvariantViolation):
    """Provider/model/gateway combination is not supported."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="UNSUPPORTED_PROVIDER_MODEL",
            details=details,
        )


def lookup_credential_reference(
    credential_ref_id: str,
    *,
    catalog: Mapping[str, CredentialReference] | None = None,
) -> CredentialReference:
    refs = catalog if catalog is not None else DEFAULT_ENV_CREDENTIAL_REFS
    ref = refs.get(credential_ref_id.strip())
    if ref is None:
        raise InvariantViolation(
            f"Unknown credential_ref_id {credential_ref_id!r}",
            code="UNKNOWN_CREDENTIAL_REF",
            details={"credential_ref_id": credential_ref_id},
        )
    return ref


def resolve_default_credential_ref(
    provider_key: ProviderKey,
    *,
    adapter_key: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> CredentialReference | None:
    """Pick an operator env credential reference without embedding secrets."""
    import os

    env = environ if environ is not None else os.environ

    if provider_key is ProviderKey.OMNIROUTE:
        if env.get("OMNIROUTE_API_KEY", "").strip():
            return DEFAULT_ENV_CREDENTIAL_REFS["env:OMNIROUTE_API_KEY"]
        return DEFAULT_ENV_CREDENTIAL_REFS["env:OMNIROUTE_API_KEY"]

    if provider_key is ProviderKey.GOOGLE or adapter_key == "gemini_cli":
        if env.get("GEMINI_API_KEY", "").strip():
            return DEFAULT_ENV_CREDENTIAL_REFS["env:GEMINI_API_KEY"]
        if env.get("GOOGLE_API_KEY", "").strip():
            return DEFAULT_ENV_CREDENTIAL_REFS["env:GOOGLE_API_KEY"]
        return DEFAULT_ENV_CREDENTIAL_REFS["env:GEMINI_API_KEY"]

    if provider_key is ProviderKey.ANTHROPIC:
        return DEFAULT_ENV_CREDENTIAL_REFS["env:ANTHROPIC_API_KEY"]
    if provider_key is ProviderKey.OPENAI:
        return DEFAULT_ENV_CREDENTIAL_REFS["env:OPENAI_API_KEY"]
    if provider_key is ProviderKey.GROQ:
        return DEFAULT_ENV_CREDENTIAL_REFS["env:GROQ_API_KEY"]
    return None


def resolve_provider_runtime(
    request: ProviderRuntimeRequest,
    *,
    environ: Mapping[str, str] | None = None,
) -> ProviderRuntimeIdentity:
    """Validate and materialize provider/model identity for execution + provenance.

    Never silently substitutes models or providers. Unsupported combinations fail.
    """
    import os

    env = environ if environ is not None else os.environ
    adapter_key = request.adapter_key.strip()
    if not adapter_key:
        raise InvariantViolation(
            "adapter_key is required to resolve provider runtime",
            code="ADAPTER_KEY_REQUIRED",
        )

    capability = get_adapter_capability(adapter_key)

    # Gateway
    if request.gateway_key:
        gateway = parse_gateway_key(request.gateway_key)
    else:
        gateway_env = (
            env.get("EVALFORGE_GATEWAY") or env.get("GATEWAY_KEY") or "direct"
        ).strip()
        gateway = parse_gateway_key(gateway_env)

    # Provider
    if request.provider_key:
        provider = parse_provider_key(request.provider_key)
    elif gateway is GatewayKey.OMNIROUTE:
        provider = ProviderKey.OMNIROUTE
    elif capability is not None:
        provider = parse_provider_key(capability.provider)
    else:
        default = _ADAPTER_DEFAULT_PROVIDER.get(adapter_key)
        if default is None:
            raise UnsupportedProviderModelError(
                f"No default provider for adapter {adapter_key!r}; "
                "set provider_key explicitly",
                details={"adapter_key": adapter_key},
            )
        provider = default

    # Routing + model
    model_raw = request.model_id
    if model_raw is None:
        model_raw = env.get("EVALFORGE_MODEL") or env.get("CODING_AGENT_MODEL")
        if model_raw is None and adapter_key == "gemini_cli":
            # Backward compatible: GEMINI_MODEL may pin the coding agent when set.
            model_raw = env.get("GEMINI_MODEL")

    routing_raw = request.routing_mode
    if routing_raw is None:
        routing_raw = env.get("EVALFORGE_ROUTING_MODE")
    if routing_raw is None:
        if model_raw and str(model_raw).strip().lower() == AUTO_MODEL_TOKEN:
            routing_raw = RoutingMode.AUTO.value
        elif model_raw and str(model_raw).strip():
            routing_raw = RoutingMode.FIXED.value
        else:
            # Legacy Gemini path: no explicit model pin — record as unspecified
            # fixed-with-unknown requested model is invalid; use honest "unset"
            # by treating absence as non-pinned experimental for metadata only
            # when live default CLI model is used. For canonical eval, require pin.
            routing_raw = RoutingMode.FIXED.value

    routing = parse_routing_mode(routing_raw)

    if routing is RoutingMode.AUTO and not request.allow_auto_routing:
        # Still allow constructing identity when explicitly requested with flag;
        # default worker path sets allow_auto_routing from env.
        auto_env = (env.get("EVALFORGE_ALLOW_AUTO_ROUTING") or "").strip().lower()
        if auto_env not in {"1", "true", "yes"} and not request.allow_auto_routing:
            raise UnsupportedProviderModelError(
                "Auto routing is experimental and disabled by default; "
                "set EVALFORGE_ALLOW_AUTO_ROUTING=1 or allow_auto_routing=True. "
                "Auto-routed results are never canonical benchmark results.",
                details={"routing_mode": "auto"},
            )

    if routing is RoutingMode.FIXED:
        if not model_raw or not str(model_raw).strip():
            # Backward compatibility: direct Gemini without explicit model pin.
            # Record routing as fixed with requested_model unset is illegal —
            # instead use a documented "provider-default" sentinel only when
            # gateway is direct and we honestly do not know the CLI default.
            if gateway is GatewayKey.DIRECT and adapter_key == "gemini_cli":
                model_raw = env.get("GEMINI_MODEL") or None
            if not model_raw or not str(model_raw).strip():
                # Honest: no pin. For fixed mode we require a model for
                # *canonical* evaluation, but legacy runs may omit it.
                # Use ModelIdentity with routing FIXED only when model present;
                # otherwise mark as non-canonical via a dedicated path below.
                pass

    # Validate unsupported combos early (no silent remap).
    _validate_provider_gateway_adapter(provider, gateway, adapter_key)

    if routing is RoutingMode.FIXED and model_raw and str(model_raw).strip():
        model_id = ModelId(str(model_raw).strip())
        if model_id.is_auto_token():
            raise UnsupportedProviderModelError(
                "Cannot use model 'auto' with fixed routing; "
                "set routing_mode=auto for experimental non-canonical runs",
                details={"model_id": model_id.value},
            )
        model = ModelIdentity(
            requested_model=model_id.value,
            actual_model=request.actual_model,
            routing_mode=RoutingMode.FIXED,
        )
    elif routing is RoutingMode.AUTO:
        requested = (
            AUTO_MODEL_TOKEN
            if not model_raw or str(model_raw).strip().lower() == AUTO_MODEL_TOKEN
            else str(model_raw).strip()
        )
        model = ModelIdentity(
            requested_model=requested,
            actual_model=request.actual_model,
            routing_mode=RoutingMode.AUTO,
        )
    else:
        # Fixed routing without an explicit model (legacy direct Gemini).
        # Represent as fixed with requested_model=None is invalid for ModelIdentity —
        # use a dedicated non-canonical identity via AUTO? No — that would lie.
        # Instead require ModelIdentity with FIXED only when model set; for legacy
        # record requested as the empty-less path using a special construction:
        # We add an optional "provider-default" literal that is NOT canonical.
        model = ModelIdentity(
            requested_model="provider-default",
            actual_model=request.actual_model,
            routing_mode=RoutingMode.FIXED,
        )
        # Mark non-canonical: provider-default is not an exact model pin.
        # is_canonical checks requested != auto; we need provider-default
        # to be non-canonical. Adjust via fallback or extend ModelIdentity.
        # Simplest: set fallback_used=None and override canonical in wrapper.

    credential_ref_id = request.credential_ref_id
    if credential_ref_id:
        lookup_credential_reference(credential_ref_id)
    else:
        default_ref = resolve_default_credential_ref(
            provider, adapter_key=adapter_key, environ=env
        )
        credential_ref_id = default_ref.id if default_ref else None

    identity = ProviderRuntimeIdentity(
        provider_key=provider,
        gateway_key=gateway,
        model=model,
        credential_ref_id=credential_ref_id,
        fallback_used=request.fallback_used,
    )

    # Exact model pin required for OmniRoute fixed routing (no silent default).
    if (
        gateway is GatewayKey.OMNIROUTE
        and routing is RoutingMode.FIXED
        and (
            identity.model.requested_model is None
            or identity.model.requested_model == "provider-default"
        )
    ):
        raise UnsupportedProviderModelError(
            "OmniRoute fixed routing requires an explicit model_id; "
            "refusing to silently select a model",
            details={"gateway_key": gateway.value, "routing_mode": routing.value},
        )

    return identity


def _validate_provider_gateway_adapter(
    provider: ProviderKey,
    gateway: GatewayKey,
    adapter_key: str,
) -> None:
    if gateway is GatewayKey.OMNIROUTE and provider not in {
        ProviderKey.OMNIROUTE,
        ProviderKey.GOOGLE,
        ProviderKey.OPENAI,
        ProviderKey.ANTHROPIC,
        ProviderKey.GROQ,
    }:
        raise UnsupportedProviderModelError(
            f"Provider {provider.value!r} is not supported via OmniRoute gateway",
            details={"provider_key": provider.value, "gateway_key": gateway.value},
        )

    if gateway is GatewayKey.DIRECT and provider is ProviderKey.OMNIROUTE:
        raise UnsupportedProviderModelError(
            "provider_key=omniroute requires gateway_key=omniroute",
            details={"provider_key": provider.value, "gateway_key": gateway.value},
        )

    # Direct Gemini remains the only live coding-agent path today.
    if (
        gateway is GatewayKey.DIRECT
        and adapter_key == "gemini_cli"
        and provider not in {ProviderKey.GOOGLE}
    ):
        raise UnsupportedProviderModelError(
            f"gemini_cli direct gateway only supports provider=google, "
            f"not {provider.value!r}",
            details={
                "adapter_key": adapter_key,
                "provider_key": provider.value,
                "gateway_key": gateway.value,
            },
        )


def is_canonical_runtime(identity: ProviderRuntimeIdentity) -> bool:
    """Canonical only when fixed routing, exact model, and no fallback."""
    if identity.fallback_used is True:
        return False
    requested = identity.model.requested_model
    if requested is None or requested in {AUTO_MODEL_TOKEN, "provider-default"}:
        return False
    return identity.model.routing_mode is RoutingMode.FIXED


def enrich_metadata_with_runtime(
    base: dict[str, str],
    identity: ProviderRuntimeIdentity,
) -> dict[str, str]:
    """Merge provider runtime identity into execution metadata (redacted)."""
    merged = dict(base)
    runtime_meta = identity.to_execution_metadata()
    # Override canonical_evaluation with stricter helper (provider-default).
    runtime_meta["canonical_evaluation"] = (
        "true" if is_canonical_runtime(identity) else "false"
    )
    merged.update(runtime_meta)
    return merged
