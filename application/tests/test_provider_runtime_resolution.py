"""Application tests for provider runtime resolution and OmniRoute gateway."""

from __future__ import annotations

from typing import Any

import pytest
from agent_eval_application.gateways import (
    EnvCredentialSecretResolver,
    InferenceRequest,
    OpenAICompatibleGateway,
    create_omniroute_gateway,
    load_omniroute_config,
)
from agent_eval_application.provider_runtime import (
    ProviderRuntimeRequest,
    UnsupportedProviderModelError,
    enrich_metadata_with_runtime,
    is_canonical_runtime,
    lookup_credential_reference,
    resolve_provider_runtime,
)
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.provider_runtime import (
    GatewayKey,
    ModelId,
    ProviderKey,
    RoutingMode,
)


def test_resolve_direct_gemini_with_explicit_model() -> None:
    identity = resolve_provider_runtime(
        ProviderRuntimeRequest(
            adapter_key="gemini_cli",
            provider_key="google",
            gateway_key="direct",
            model_id="gemini-2.0-flash",
            routing_mode="fixed",
        ),
        environ={},
    )
    assert identity.provider_key is ProviderKey.GOOGLE
    assert identity.gateway_key is GatewayKey.DIRECT
    assert identity.model.requested_model == "gemini-2.0-flash"
    assert is_canonical_runtime(identity) is True
    meta = enrich_metadata_with_runtime({"adapter_key": "gemini_cli"}, identity)
    assert meta["canonical_evaluation"] == "true"
    assert meta["credential_ref_id"] == "env:GEMINI_API_KEY"
    assert "sk-" not in str(meta)


def test_legacy_gemini_without_model_pin_is_non_canonical() -> None:
    identity = resolve_provider_runtime(
        ProviderRuntimeRequest(
            adapter_key="gemini_cli",
            gateway_key="direct",
        ),
        environ={},
    )
    assert identity.gateway_key is GatewayKey.DIRECT
    assert identity.model.requested_model == "provider-default"
    assert is_canonical_runtime(identity) is False


def test_unsupported_provider_for_gemini_direct_fails() -> None:
    with pytest.raises(UnsupportedProviderModelError, match="provider=google"):
        resolve_provider_runtime(
            ProviderRuntimeRequest(
                adapter_key="gemini_cli",
                provider_key="openai",
                gateway_key="direct",
                model_id="gpt-4o",
                routing_mode="fixed",
            ),
            environ={},
        )


def test_no_silent_auto_without_allow_flag() -> None:
    with pytest.raises(UnsupportedProviderModelError, match="Auto routing"):
        resolve_provider_runtime(
            ProviderRuntimeRequest(
                adapter_key="gemini_cli",
                gateway_key="omniroute",
                model_id="auto",
                routing_mode="auto",
                allow_auto_routing=False,
            ),
            environ={},
        )


def test_auto_routing_marked_non_canonical_when_allowed() -> None:
    identity = resolve_provider_runtime(
        ProviderRuntimeRequest(
            adapter_key="gemini_cli",
            gateway_key="omniroute",
            provider_key="omniroute",
            model_id="auto",
            routing_mode="auto",
            allow_auto_routing=True,
            actual_model="gemini-2.0-flash",
        ),
        environ={"OMNIROUTE_API_KEY": "test-key-not-real"},
    )
    assert identity.model.routing_mode is RoutingMode.AUTO
    assert is_canonical_runtime(identity) is False
    assert identity.model.actual_model == "gemini-2.0-flash"


def test_fixed_routing_rejects_model_auto_token() -> None:
    with pytest.raises(UnsupportedProviderModelError, match="auto"):
        resolve_provider_runtime(
            ProviderRuntimeRequest(
                adapter_key="gemini_cli",
                gateway_key="direct",
                model_id="auto",
                routing_mode="fixed",
            ),
            environ={},
        )


def test_omniroute_fixed_requires_explicit_model() -> None:
    with pytest.raises(UnsupportedProviderModelError, match="explicit model"):
        resolve_provider_runtime(
            ProviderRuntimeRequest(
                adapter_key="gemini_cli",
                gateway_key="omniroute",
                provider_key="omniroute",
                routing_mode="fixed",
            ),
            environ={"OMNIROUTE_API_KEY": "x"},
        )


def test_credential_ref_lookup_does_not_expose_secret() -> None:
    ref = lookup_credential_reference("env:GEMINI_API_KEY")
    public = ref.to_public_dict()
    assert "secret" not in public
    assert public["env_var_name"] == "GEMINI_API_KEY"


def test_omniroute_config_parsing_without_secret_in_config() -> None:
    cfg = load_omniroute_config(
        environ={
            "OMNIROUTE_BASE_URL": "https://gateway.example.com",
            "OMNIROUTE_API_KEY": "super-secret-key-value",
            "OMNIROUTE_TIMEOUT_SECONDS": "30",
        }
    )
    assert cfg is not None
    assert cfg.base_url == "https://gateway.example.com"
    assert cfg.credential_ref_id == "env:OMNIROUTE_API_KEY"
    assert cfg.timeout_seconds == 30.0
    assert "super-secret" not in str(cfg)
    assert "super-secret" not in repr(cfg)


def test_omniroute_config_absent_when_unset() -> None:
    assert load_omniroute_config(environ={}) is None


def test_omniroute_config_requires_both_url_and_key() -> None:
    with pytest.raises(InvariantViolation, match="OMNIROUTE_BASE_URL"):
        load_omniroute_config(environ={"OMNIROUTE_API_KEY": "x"})
    with pytest.raises(InvariantViolation, match="OMNIROUTE_API_KEY"):
        load_omniroute_config(
            environ={"OMNIROUTE_BASE_URL": "https://gateway.example.com"}
        )


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ):
        # Ensure Authorization is present but never assert/log the secret value
        # into test failure messages beyond presence.
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(
            {
                "model": "gemini-2.0-flash-001",
                "choices": [
                    {"message": {"content": "ok"}},
                ],
                "fallback_used": False,
            }
        )


def test_openai_compatible_gateway_records_actual_model_without_secret_leak() -> None:
    http = _FakeHttp()
    gateway = OpenAICompatibleGateway(
        config=load_omniroute_config(
            environ={
                "OMNIROUTE_BASE_URL": "https://gateway.example.com",
                "OMNIROUTE_API_KEY": "test-secret-do-not-leak",
            }
        ),  # type: ignore[arg-type]
        secrets=EnvCredentialSecretResolver(
            environ={"OMNIROUTE_API_KEY": "test-secret-do-not-leak"}
        ),
        http_client=http,
    )
    assert gateway is not None
    response = gateway.complete(
        InferenceRequest(
            model=ModelId("gemini-2.0-flash"),
            messages=({"role": "user", "content": "ping"},),
            routing_mode=RoutingMode.FIXED,
        )
    )
    assert response.requested_model == "gemini-2.0-flash"
    assert response.actual_model == "gemini-2.0-flash-001"
    assert response.fallback_used is False
    assert response.content == "ok"
    assert http.calls[0]["json"]["model"] == "gemini-2.0-flash"
    # Response / public objects must not embed the API key.
    assert "test-secret-do-not-leak" not in str(response)
    assert "test-secret-do-not-leak" not in str(response.raw)


def test_gateway_fixed_routing_rejects_auto_model() -> None:
    gateway = create_omniroute_gateway(
        environ={
            "OMNIROUTE_BASE_URL": "https://gateway.example.com",
            "OMNIROUTE_API_KEY": "x",
        },
        http_client=_FakeHttp(),
    )
    assert gateway is not None
    with pytest.raises(InvariantViolation, match="auto"):
        gateway.complete(
            InferenceRequest(
                model=ModelId("auto"),
                messages=({"role": "user", "content": "ping"},),
                routing_mode=RoutingMode.FIXED,
            )
        )


def test_create_omniroute_gateway_none_when_unconfigured() -> None:
    assert create_omniroute_gateway(environ={}) is None
