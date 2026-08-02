"""Anthropic Messages API configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from agent_eval_graders.providers.config import (
    ProviderConfig,
    env_str,
    load_common_knobs,
    require_api_key,
)

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_API_VERSION = "2023-06-01"
_UNSET = object()


@dataclass(frozen=True, slots=True)
class AnthropicJudgeConfig:
    """Config for the Anthropic judge provider (``ANTHROPIC_API_KEY``)."""

    api_key: str
    model: str = DEFAULT_ANTHROPIC_MODEL
    timeout_seconds: float = 60.0
    retry_count: int = 2
    temperature: float = 0.0
    seed: int | None = 0
    max_tokens: int = 2048
    base_url: str = DEFAULT_BASE_URL
    api_version: str = ANTHROPIC_API_VERSION

    def __post_init__(self) -> None:
        ProviderConfig(
            api_key=self.api_key,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
            retry_count=self.retry_count,
            temperature=self.temperature,
            seed=self.seed,
            max_tokens=self.max_tokens,
            base_url=self.base_url,
        )

    @classmethod
    def from_env(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        temperature: float | None = None,
        seed: object = _UNSET,
        max_tokens: int | None = None,
        base_url: str | None = None,
    ) -> AnthropicJudgeConfig:
        knobs = load_common_knobs(environ=environ, prefix="ANTHROPIC")
        resolved_seed: int | None = (
            knobs["seed"] if seed is _UNSET else seed  # type: ignore[assignment]
        )
        return cls(
            api_key=require_api_key(
                "ANTHROPIC_API_KEY",
                environ=environ,
                explicit=api_key,
            ),
            model=model
            or env_str("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL, environ=environ)
            or DEFAULT_ANTHROPIC_MODEL,
            timeout_seconds=(
                timeout_seconds
                if timeout_seconds is not None
                else float(knobs["timeout_seconds"])
            ),
            retry_count=(
                retry_count if retry_count is not None else int(knobs["retry_count"])
            ),
            temperature=(
                temperature if temperature is not None else float(knobs["temperature"])
            ),
            seed=resolved_seed,
            max_tokens=(
                max_tokens if max_tokens is not None else int(knobs["max_tokens"])
            ),
            base_url=base_url or knobs.get("base_url") or DEFAULT_BASE_URL,
        )
