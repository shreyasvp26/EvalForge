"""Application tests for provider connection verification use cases."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.provider_verification import (
    ProviderModelInfo,
    VerificationResult,
    VerificationStatus,
)
from agent_eval_application.use_cases.provider_connections import (
    CreateProviderConnection,
    CreateProviderConnectionCommand,
    ListConnectionModels,
    ListConnectionModelsQuery,
    VerifyProviderConnection,
    VerifyProviderConnectionCommand,
)
from agent_eval_infrastructure.auth import InMemoryProviderConnectionStore
from agent_eval_infrastructure.secrets.fernet_box import _derive_fernet_key


class FakeVerifier:
    def __init__(self, result: VerificationResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def verify_api_key(self, provider_key: str, api_key: str) -> VerificationResult:
        self.calls.append((provider_key, api_key))
        return self.result

    def list_available_models(
        self, provider_key: str, api_key: str
    ) -> tuple[ProviderModelInfo, ...]:
        result = self.verify_api_key(provider_key, api_key)
        if result.status is not VerificationStatus.VALID:
            raise ValueError(result.message)
        return result.models


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> InMemoryProviderConnectionStore:
    raw = "test-provider-credentials-key-32chars!!"
    monkeypatch.setenv("PROVIDER_CREDENTIALS_KEY", raw)
    return InMemoryProviderConnectionStore(secret_key=_derive_fernet_key(raw))


def test_verify_enriches_catalog_models(
    store: InMemoryProviderConnectionStore,
) -> None:
    actor = Actor(id="alice")
    conn = CreateProviderConnection(store).execute(
        CreateProviderConnectionCommand(
            actor=actor,
            provider_key="google",
            api_key="live-google-key",
            display_name="Google",
        )
    )
    verifier = FakeVerifier(
        VerificationResult(
            status=VerificationStatus.VALID,
            provider_key="google",
            message="API key accepted",
            checked_at=datetime(2026, 8, 26, tzinfo=UTC),
            models=(
                ProviderModelInfo("gemini-2.0-flash", "Gemini 2.0 Flash"),
                ProviderModelInfo("unknown-live-model", "Unknown Live"),
            ),
        )
    )
    result = VerifyProviderConnection(store, verifier).execute(
        VerifyProviderConnectionCommand(actor=actor, connection_id=conn.id)
    )
    assert result.status == "valid"
    assert verifier.calls == [("google", "live-google-key")]
    by_id = {m.model_id: m for m in result.models}
    assert by_id["gemini-2.0-flash"].in_catalog is True
    assert "gemini_cli" in by_id["gemini-2.0-flash"].adapter_keys
    assert by_id["unknown-live-model"].in_catalog is False
    assert by_id["unknown-live-model"].adapter_keys == ()
    assert "live-google-key" not in str(result)


def test_list_models_rejects_invalid_key(
    store: InMemoryProviderConnectionStore,
) -> None:
    actor = Actor(id="alice")
    conn = CreateProviderConnection(store).execute(
        CreateProviderConnectionCommand(
            actor=actor,
            provider_key="google",
            api_key="bad-key",
            display_name="Google",
        )
    )
    verifier = FakeVerifier(
        VerificationResult(
            status=VerificationStatus.INVALID,
            provider_key="google",
            message="Provider rejected the API key (HTTP 401)",
            checked_at=datetime(2026, 8, 26, tzinfo=UTC),
            models=(),
        )
    )
    with pytest.raises(ApplicationValidationError, match="rejected"):
        ListConnectionModels(store, verifier).execute(
            ListConnectionModelsQuery(actor=actor, connection_id=conn.id)
        )
