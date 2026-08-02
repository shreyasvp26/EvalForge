"""OpenAI ``JudgeProvider`` — implements the existing rubric port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from agent_eval_graders.providers.determinism import (
    effective_settings,
    resolve_max_tokens,
    resolve_model,
    resolve_seed,
    resolve_temperature,
)
from agent_eval_graders.providers.openai.client import OpenAIClient
from agent_eval_graders.providers.openai.config import OpenAIJudgeConfig
from agent_eval_graders.providers.retry import call_with_retry
from agent_eval_graders.rubric.models import JudgeRawResponse, JudgeRequest


@dataclass
class OpenAIJudgeProvider:
    """Production OpenAI Chat Completions judge. Seed is supported."""

    config: OpenAIJudgeConfig
    http_client: httpx.Client | None = None
    _client: OpenAIClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = OpenAIClient(self.config, http_client=self.http_client)

    @property
    def client(self) -> OpenAIClient:
        assert self._client is not None
        return self._client

    def complete(self, request: JudgeRequest) -> JudgeRawResponse:
        model = resolve_model(request.controls, self.config)
        temperature = resolve_temperature(request.controls, self.config)
        seed = resolve_seed(request.controls, self.config)
        max_tokens = resolve_max_tokens(request.controls, self.config)
        timeout = min(request.timeout_seconds, self.config.timeout_seconds)

        def operation() -> tuple[str, str, float, dict[str, Any]]:
            return self.client.complete(
                system=request.prompt.system,
                user=request.prompt.user,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                timeout_seconds=timeout,
                correlation_id=request.correlation_id,
            )

        content, used_model, latency_ms, raw_meta = call_with_retry(
            operation,
            retry_count=self.config.retry_count,
        )
        settings = effective_settings(
            provider="openai",
            model=used_model,
            temperature=temperature,
            seed=seed,
            seed_supported=True,
            max_tokens=max_tokens,
            model_hint=request.controls.model_hint,
        )
        return JudgeRawResponse(
            content=content,
            model=used_model,
            latency_ms=latency_ms,
            metadata={**settings, "vendor": raw_meta},
        )
