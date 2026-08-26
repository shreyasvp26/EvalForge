"""Unit tests for HttpProviderVerifier (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
from agent_eval_application.ports.provider_verification import VerificationStatus
from agent_eval_infrastructure.providers.verifier import HttpProviderVerifier


def _verifier_with(handler: httpx.MockTransport) -> HttpProviderVerifier:
    return HttpProviderVerifier(timeout_seconds=2.0, transport=handler)


def test_google_valid_lists_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers.get("x-goog-api-key") == "google-secret"
        assert "key=" not in str(request.url)
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemini-2.0-flash",
                        "displayName": "Gemini 2.0 Flash",
                    },
                    {"name": "models/gemini-2.5-pro", "displayName": "Gemini 2.5 Pro"},
                ]
            },
        )

    result = _verifier_with(httpx.MockTransport(handler)).verify_api_key(
        "google", "google-secret"
    )
    assert result.status is VerificationStatus.VALID
    assert [m.model_id for m in result.models] == [
        "gemini-2.0-flash",
        "gemini-2.5-pro",
    ]
    assert "google-secret" not in result.message


def test_google_invalid_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "API key not valid"}})

    result = _verifier_with(httpx.MockTransport(handler)).verify_api_key(
        "google", "bad-key"
    )
    assert result.status is VerificationStatus.INVALID
    assert result.models == ()
    assert "bad-key" not in result.message


def test_anthropic_valid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == "anth-secret"
        assert request.headers.get("anthropic-version")
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "claude-sonnet-4-20250514",
                        "display_name": "Claude Sonnet 4",
                    }
                ]
            },
        )

    result = _verifier_with(httpx.MockTransport(handler)).verify_api_key(
        "anthropic", "anth-secret"
    )
    assert result.status is VerificationStatus.VALID
    assert result.models[0].model_id == "claude-sonnet-4-20250514"


def test_openai_valid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == "Bearer oa-secret"
        return httpx.Response(200, json={"data": [{"id": "gpt-4o"}]})

    result = _verifier_with(httpx.MockTransport(handler)).verify_api_key(
        "openai", "oa-secret"
    )
    assert result.status is VerificationStatus.VALID
    assert result.models[0].model_id == "gpt-4o"


def test_timeout_is_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    result = _verifier_with(httpx.MockTransport(handler)).verify_api_key(
        "google", "google-secret"
    )
    assert result.status is VerificationStatus.ERROR
    assert "timed out" in result.message.lower() or "timeout" in result.message.lower()


def test_omniroute_unsupported() -> None:
    result = HttpProviderVerifier().verify_api_key("omniroute", "anything")
    assert result.status is VerificationStatus.ERROR
    assert "OmniRoute" in result.message


def test_list_available_models_raises_on_invalid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={})

    verifier = _verifier_with(httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="rejected"):
        verifier.list_available_models("google", "bad")
