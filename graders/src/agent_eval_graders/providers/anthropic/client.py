"""Anthropic Messages HTTP client — no vendor SDK dependency."""

from __future__ import annotations

import time
from typing import Any

import httpx

from agent_eval_graders.providers.anthropic.config import AnthropicJudgeConfig
from agent_eval_graders.providers.errors import JudgeInvalidResponseError
from agent_eval_graders.providers.http import map_http_status, map_httpx_transport_error


class AnthropicClient:
    """Thin HTTP client for ``POST /v1/messages``."""

    def __init__(
        self,
        config: AnthropicJudgeConfig,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout_seconds,
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": config.api_version,
                "content-type": "application/json",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> AnthropicClient:
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
        timeout_seconds: float,
        correlation_id: str,
    ) -> tuple[str, str, float, dict[str, Any]]:
        """Return ``(content, model, latency_ms, raw_metadata)``."""
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        started = time.monotonic()
        try:
            response = self._client.post(
                "/v1/messages",
                json=payload,
                timeout=timeout_seconds,
            )
        except httpx.HTTPError as exc:
            map_httpx_transport_error(
                exc,
                provider="anthropic",
                correlation_id=correlation_id,
            )
            raise  # pragma: no cover — map always raises

        latency_ms = (time.monotonic() - started) * 1000.0
        body_text = response.text
        map_http_status(
            response.status_code,
            provider="anthropic",
            body_preview=body_text,
            correlation_id=correlation_id,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise JudgeInvalidResponseError(
                "Anthropic response was not valid JSON",
                details={
                    "provider": "anthropic",
                    "correlation_id": correlation_id,
                    "body_preview": body_text[:200],
                },
                cause=exc,
            ) from exc

        content = _extract_text(data, correlation_id=correlation_id)
        used_model = str(data.get("model") or model)
        meta = {
            "stop_reason": data.get("stop_reason"),
            "usage": data.get("usage"),
            "id": data.get("id"),
        }
        return content, used_model, latency_ms, meta


def _extract_text(data: object, *, correlation_id: str) -> str:
    if not isinstance(data, dict):
        raise JudgeInvalidResponseError(
            "Anthropic response root must be an object",
            details={"provider": "anthropic", "correlation_id": correlation_id},
        )
    blocks = data.get("content")
    if not isinstance(blocks, list) or not blocks:
        raise JudgeInvalidResponseError(
            "Anthropic response missing content blocks",
            details={"provider": "anthropic", "correlation_id": correlation_id},
        )
    texts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
    if not texts:
        raise JudgeInvalidResponseError(
            "Anthropic response contained no text content",
            details={"provider": "anthropic", "correlation_id": correlation_id},
        )
    return "\n".join(texts)
