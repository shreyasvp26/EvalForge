"""Live provider API-key verification via minimal authenticated HTTP calls.

Timeout-protected. Never logs API keys or response bodies that may contain
sensitive material beyond model ids/names.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from agent_eval_application.ports.provider_verification import (
    ProviderModelInfo,
    VerificationResult,
    VerificationStatus,
)

_DEFAULT_TIMEOUT = 15.0

# Provider list-models endpoints (public REST). Keys travel only as headers/query.
_GOOGLE_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
_OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
_ANTHROPIC_VERSION = "2023-06-01"


def _now() -> datetime:
    return datetime.now(UTC)


def _safe_message(exc: BaseException) -> str:
    """Human-readable error without echoing secrets from request URLs/headers."""
    text = str(exc).strip() or exc.__class__.__name__
    # Strip query strings that might include ?key=
    if "?" in text:
        text = text.split("?", 1)[0]
    if len(text) > 240:
        text = text[:237] + "..."
    return text


class HttpProviderVerifier:
    """Real HTTP implementations for Google, Anthropic, and OpenAI model listing."""

    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._transport = transport

    def verify_api_key(self, provider_key: str, api_key: str) -> VerificationResult:
        key = provider_key.strip().lower()
        secret = api_key.strip()
        if not secret:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                provider_key=key,
                message="API key is empty",
                checked_at=_now(),
                models=(),
            )
        try:
            models = self._list_models(key, secret)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                return VerificationResult(
                    status=VerificationStatus.INVALID,
                    provider_key=key,
                    message=f"Provider rejected the API key (HTTP {status_code})",
                    checked_at=_now(),
                    models=(),
                )
            return VerificationResult(
                status=VerificationStatus.ERROR,
                provider_key=key,
                message=f"Provider returned HTTP {status_code}",
                checked_at=_now(),
                models=(),
            )
        except httpx.TimeoutException:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                provider_key=key,
                message="Provider request timed out",
                checked_at=_now(),
                models=(),
            )
        except httpx.HTTPError as exc:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                provider_key=key,
                message=f"Provider request failed: {_safe_message(exc)}",
                checked_at=_now(),
                models=(),
            )
        except ValueError as exc:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                provider_key=key,
                message=str(exc),
                checked_at=_now(),
                models=(),
            )

        return VerificationResult(
            status=VerificationStatus.VALID,
            provider_key=key,
            message="API key accepted",
            checked_at=_now(),
            models=models,
        )

    def list_available_models(
        self, provider_key: str, api_key: str
    ) -> tuple[ProviderModelInfo, ...]:
        result = self.verify_api_key(provider_key, api_key)
        if result.status is not VerificationStatus.VALID:
            raise ValueError(result.message)
        return result.models

    def _client(self) -> httpx.Client:
        kwargs: dict[str, Any] = {"timeout": self._timeout}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _list_models(
        self, provider_key: str, api_key: str
    ) -> tuple[ProviderModelInfo, ...]:
        if provider_key == "google":
            return self._list_google(api_key)
        if provider_key == "anthropic":
            return self._list_anthropic(api_key)
        if provider_key == "openai":
            return self._list_openai(api_key)
        if provider_key == "omniroute":
            raise ValueError(
                "OmniRoute credentials cannot be verified via a direct model list API"
            )
        raise ValueError(f"Verification is not supported for provider {provider_key!r}")

    def _list_google(self, api_key: str) -> tuple[ProviderModelInfo, ...]:
        # Prefer header over ?key= so timeouts/errors never echo the secret in URLs.
        with self._client() as client:
            response = client.get(
                _GOOGLE_MODELS_URL,
                params={"pageSize": 100},
                headers={"x-goog-api-key": api_key},
            )
            response.raise_for_status()
            payload = response.json()
        models: list[ProviderModelInfo] = []
        for item in payload.get("models") or []:
            raw_name = str(item.get("name") or "").strip()
            if not raw_name:
                continue
            # Google returns "models/gemini-2.0-flash"
            model_id = raw_name.removeprefix("models/")
            display = str(item.get("displayName") or model_id).strip() or model_id
            models.append(ProviderModelInfo(model_id=model_id, display_name=display))
        return tuple(models)

    def _list_anthropic(self, api_key: str) -> tuple[ProviderModelInfo, ...]:
        with self._client() as client:
            response = client.get(
                _ANTHROPIC_MODELS_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                },
            )
            response.raise_for_status()
            payload = response.json()
        models: list[ProviderModelInfo] = []
        for item in payload.get("data") or []:
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue
            display = str(item.get("display_name") or model_id).strip() or model_id
            models.append(ProviderModelInfo(model_id=model_id, display_name=display))
        return tuple(models)

    def _list_openai(self, api_key: str) -> tuple[ProviderModelInfo, ...]:
        with self._client() as client:
            response = client.get(
                _OPENAI_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
        models: list[ProviderModelInfo] = []
        for item in payload.get("data") or []:
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue
            models.append(ProviderModelInfo(model_id=model_id, display_name=model_id))
        return tuple(models)
