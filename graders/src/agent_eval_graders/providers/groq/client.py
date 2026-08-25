"""Groq Chat Completions HTTP client — OpenAI-compatible, no vendor SDK."""

from __future__ import annotations

import time
from typing import Any

import httpx

from agent_eval_graders.providers.errors import JudgeInvalidResponseError
from agent_eval_graders.providers.groq.config import GroqJudgeConfig
from agent_eval_graders.providers.http import map_http_status, map_httpx_transport_error


class GroqClient:
    """Thin HTTP client for Groq ``POST /chat/completions``."""

    def __init__(
        self,
        config: GroqJudgeConfig,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=config.timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "content-type": "application/json",
            },
        )
        self._completions_url = f"{config.base_url.rstrip('/')}/chat/completions"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GroqClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None,
        timeout_seconds: float,
        correlation_id: str,
    ) -> tuple[str, str, float, dict[str, Any]]:
        """Return ``(content, model, latency_ms, raw_metadata)``."""
        payload: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if seed is not None:
            payload["seed"] = seed

        started = time.monotonic()
        try:
            response = self._client.post(
                self._completions_url,
                json=payload,
                timeout=timeout_seconds,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "content-type": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            map_httpx_transport_error(
                exc,
                provider="groq",
                correlation_id=correlation_id,
            )
            raise  # pragma: no cover

        latency_ms = (time.monotonic() - started) * 1000.0
        body_text = response.text
        map_http_status(
            response.status_code,
            provider="groq",
            body_preview=body_text,
            correlation_id=correlation_id,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise JudgeInvalidResponseError(
                "Groq response was not valid JSON",
                details={
                    "provider": "groq",
                    "correlation_id": correlation_id,
                    "body_preview": body_text[:200],
                },
                cause=exc,
            ) from exc

        content = _extract_text(data, correlation_id=correlation_id)
        used_model = str(data.get("model") or model)
        meta = {
            "id": data.get("id"),
            "usage": data.get("usage"),
            "finish_reason": _finish_reason(data),
            "system_fingerprint": data.get("system_fingerprint"),
        }
        return content, used_model, latency_ms, meta


def _finish_reason(data: dict[str, Any]) -> object:
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0].get("finish_reason")
    return None


def _extract_text(data: object, *, correlation_id: str) -> str:
    if not isinstance(data, dict):
        raise JudgeInvalidResponseError(
            "Groq response root must be an object",
            details={"provider": "groq", "correlation_id": correlation_id},
        )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise JudgeInvalidResponseError(
            "Groq response missing choices",
            details={"provider": "groq", "correlation_id": correlation_id},
        )
    first = choices[0]
    if not isinstance(first, dict):
        raise JudgeInvalidResponseError(
            "Groq choice must be an object",
            details={"provider": "groq", "correlation_id": correlation_id},
        )
    message = first.get("message")
    if not isinstance(message, dict):
        raise JudgeInvalidResponseError(
            "Groq choice missing message",
            details={"provider": "groq", "correlation_id": correlation_id},
        )
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise JudgeInvalidResponseError(
            "Groq message content must be a non-empty string",
            details={"provider": "groq", "correlation_id": correlation_id},
        )
    return content
