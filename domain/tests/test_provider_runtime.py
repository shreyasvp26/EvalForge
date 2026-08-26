"""Domain tests for provider / model / gateway runtime identity."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.configuration import sanitize_execution_metadata
from agent_eval_domain.execution.credentials import (
    CredentialBackend,
    CredentialReference,
)
from agent_eval_domain.execution.provider_runtime import (
    GatewayKey,
    ModelId,
    ModelIdentity,
    ProviderKey,
    ProviderRuntimeIdentity,
    RoutingMode,
    provider_runtime_from_metadata,
)


def test_provider_gateway_model_identity_round_trip() -> None:
    identity = ProviderRuntimeIdentity(
        provider_key=ProviderKey.GOOGLE,
        gateway_key=GatewayKey.DIRECT,
        model=ModelIdentity(
            requested_model="gemini-2.0-flash",
            actual_model="gemini-2.0-flash",
            routing_mode=RoutingMode.FIXED,
        ),
        credential_ref_id="env:GEMINI_API_KEY",
        fallback_used=False,
    )
    meta = identity.to_execution_metadata()
    cleaned = sanitize_execution_metadata(meta)
    assert cleaned["provider_key"] == "google"
    assert cleaned["gateway_key"] == "direct"
    assert cleaned["requested_model"] == "gemini-2.0-flash"
    assert cleaned["actual_model"] == "gemini-2.0-flash"
    assert cleaned["routing_mode"] == "fixed"
    assert cleaned["canonical_evaluation"] == "true"
    assert cleaned["credential_ref_id"] == "env:GEMINI_API_KEY"
    assert cleaned["fallback_used"] == "false"
    assert "sk-" not in str(cleaned)

    restored = provider_runtime_from_metadata(cleaned)
    assert restored is not None
    assert restored.provider_key is ProviderKey.GOOGLE
    assert restored.model.requested_model == "gemini-2.0-flash"
    assert restored.is_canonical_evaluation is True


def test_fixed_routing_rejects_auto_model() -> None:
    with pytest.raises(InvariantViolation, match="auto"):
        ModelIdentity(
            requested_model="auto",
            actual_model=None,
            routing_mode=RoutingMode.FIXED,
        )


def test_fixed_routing_requires_explicit_model() -> None:
    with pytest.raises(InvariantViolation, match="explicit requested_model"):
        ModelIdentity(
            requested_model=None,
            actual_model=None,
            routing_mode=RoutingMode.FIXED,
        )


def test_auto_routing_is_not_canonical() -> None:
    identity = ProviderRuntimeIdentity(
        provider_key=ProviderKey.OMNIROUTE,
        gateway_key=GatewayKey.OMNIROUTE,
        model=ModelIdentity(
            requested_model="auto",
            actual_model="gemini-2.0-flash",
            routing_mode=RoutingMode.AUTO,
        ),
    )
    assert identity.is_canonical_evaluation is False
    assert identity.to_execution_metadata()["canonical_evaluation"] == "false"


def test_fallback_makes_result_non_canonical() -> None:
    identity = ProviderRuntimeIdentity(
        provider_key=ProviderKey.GOOGLE,
        gateway_key=GatewayKey.DIRECT,
        model=ModelIdentity(
            requested_model="gemini-2.0-flash",
            actual_model="gemini-1.5-pro",
            routing_mode=RoutingMode.FIXED,
        ),
        fallback_used=True,
    )
    assert identity.is_canonical_evaluation is False


def test_model_id_rejects_empty() -> None:
    with pytest.raises(InvariantViolation):
        ModelId("  ")


def test_omniroute_provider_requires_omniroute_gateway() -> None:
    with pytest.raises(InvariantViolation, match="gateway_key=omniroute"):
        ProviderRuntimeIdentity(
            provider_key=ProviderKey.OMNIROUTE,
            gateway_key=GatewayKey.DIRECT,
            model=ModelIdentity(
                requested_model="gpt-4o",
                actual_model=None,
                routing_mode=RoutingMode.FIXED,
            ),
        )


def test_credential_reference_never_holds_secret() -> None:
    ref = CredentialReference(
        id="env:GEMINI_API_KEY",
        provider_key=ProviderKey.GOOGLE,
        label="Operator Gemini",
        backend=CredentialBackend.ENVIRONMENT,
        env_var_name="GEMINI_API_KEY",
    )
    public = ref.to_public_dict()
    assert public["credential_ref_id"] == "env:GEMINI_API_KEY"
    assert public["env_var_name"] == "GEMINI_API_KEY"
    assert "sk-" not in str(public)
    assert not hasattr(ref, "secret")
    assert not hasattr(ref, "api_key")


def test_credential_reference_rejects_secretish_id() -> None:
    with pytest.raises(InvariantViolation, match="secret"):
        CredentialReference(
            id="sk-live-abcdef",
            provider_key=ProviderKey.OPENAI,
            label="bad",
            env_var_name="OPENAI_API_KEY",
        )


def test_sanitize_keeps_provider_model_keys_drops_secrets() -> None:
    cleaned = sanitize_execution_metadata(
        {
            "provider_key": "google",
            "gateway_key": "direct",
            "requested_model": "gemini-2.0-flash",
            "routing_mode": "fixed",
            "canonical_evaluation": "true",
            "credential_ref_id": "env:GEMINI_API_KEY",
            "api_key": "sk-secret",
            "OMNIROUTE_API_KEY": "should-drop",
        }
    )
    assert cleaned["provider_key"] == "google"
    assert cleaned["requested_model"] == "gemini-2.0-flash"
    assert "api_key" not in cleaned
    assert "OMNIROUTE_API_KEY" not in cleaned
