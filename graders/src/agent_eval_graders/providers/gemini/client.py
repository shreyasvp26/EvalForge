"""Google Gemini generateContent HTTP client — no vendor SDK dependency."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx

from agent_eval_graders.providers.errors import JudgeInvalidResponseError
from agent_eval_graders.providers.gemini.config import GeminiJudgeConfig
from agent_eval_graders.providers.http import map_http_status, map_httpx_transport_error


class GeminiClient:
    """Thin HTTP client for ``models/{model}:generateContent``."""

    def __init__(
        self,
        config: GeminiJudgeConfig,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout_seconds,
            headers={"content-type": "application/json"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GeminiClient:
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
        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if seed is not None:
            generation_config["seed"] = seed

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation_config,
        }
        path = f"/models/{quote(model, safe='')}:generateContent"

        started = time.monotonic()
        try:
            response = self._client.post(
                path,
                params={"key": self._config.api_key},
                json=payload,
                timeout=timeout_seconds,
            )
        except httpx.HTTPError as exc:
            map_httpx_transport_error(
                exc,
                provider="gemini",
                correlation_id=correlation_id,
            )
            raise  # pragma: no cover

        latency_ms = (time.monotonic() - started) * 1000.0
        body_text = response.text
        map_http_status(
            response.status_code,
            provider="gemini",
            body_preview=body_text,
            correlation_id=correlation_id,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise JudgeInvalidResponseError(
                "Gemini response was not valid JSON",
                details={
                    "provider": "gemini",
                    "correlation_id": correlation_id,
                    "body_preview": body_text[:200],
                },
                cause=exc,
            ) from exc

        content = _extract_text(data, correlation_id=correlation_id)
        usage = data.get("usageMetadata") if isinstance(data, dict) else None
        version = data.get("modelVersion") if isinstance(data, dict) else None
        meta = {
            "usageMetadata": usage,
            "modelVersion": version,
            "finishReason": _finish_reason(data),
        }
        return content, model, latency_ms, meta


def _finish_reason(data: object) -> object:
    if not isinstance(data, dict):
        return None
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        return candidates[0].get("finishReason")
    return None


def _extract_text(data: object, *, correlation_id: str) -> str:
    if not isinstance(data, dict):
        raise JudgeInvalidResponseError(
            "Gemini response root must be an object",
            details={"provider": "gemini", "correlation_id": correlation_id},
        )
    # Prompt / safety blocks surface as an empty candidates list.
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise JudgeInvalidResponseError(
            "Gemini response missing candidates",
            details={
                "provider": "gemini",
                "correlation_id": correlation_id,
                "promptFeedback": data.get("promptFeedback"),
            },
        )
    first = candidates[0]
    if not isinstance(first, dict):
        raise JudgeInvalidResponseError(
            "Gemini candidate must be an object",
            details={"provider": "gemini", "correlation_id": correlation_id},
        )
    content = first.get("content")
    if not isinstance(content, dict):
        raise JudgeInvalidResponseError(
            "Gemini candidate missing content",
            details={"provider": "gemini", "correlation_id": correlation_id},
        )
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise JudgeInvalidResponseError(
            "Gemini content missing parts",
            details={"provider": "gemini", "correlation_id": correlation_id},
        )
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"])
    if not texts:
        raise JudgeInvalidResponseError(
            "Gemini response contained no text parts",
            details={"provider": "gemini", "correlation_id": correlation_id},
        )
    return "\n".join(texts)
