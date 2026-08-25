"""Judge provider selection — construct a production JudgeProvider by name."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from agent_eval_graders.rubric.ports import JudgeProvider

ProviderName = Literal["anthropic", "openai", "gemini", "groq", "mock"]


def normalize_provider_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def create_judge_provider(
    name: str,
    *,
    environ: Mapping[str, str] | None = None,
    **overrides: object,
) -> JudgeProvider:
    """Build a production (or mock) judge provider by name.

    Supported names: ``anthropic``, ``openai``, ``gemini``, ``groq``, ``mock``.
    Vendor SDKs are imported lazily so unused providers stay optional at
    import time.
    """
    key = normalize_provider_name(name)
    if key in {"mock", "mock-judge"}:
        from agent_eval_graders.rubric.judge import MockJudgeProvider

        response = overrides.get("response")
        if isinstance(response, str):
            return MockJudgeProvider(response=response)
        return MockJudgeProvider()

    if key == "anthropic":
        from agent_eval_graders.providers.anthropic.config import (
            AnthropicJudgeConfig,
        )
        from agent_eval_graders.providers.anthropic.provider import (
            AnthropicJudgeProvider,
        )

        config = overrides.get("config")
        if not isinstance(config, AnthropicJudgeConfig):
            config = AnthropicJudgeConfig.from_env(
                environ=environ,
                **_filter_config(overrides),
            )
        return AnthropicJudgeProvider(config=config)

    if key in {"openai", "open-ai"}:
        from agent_eval_graders.providers.openai.config import OpenAIJudgeConfig
        from agent_eval_graders.providers.openai.provider import OpenAIJudgeProvider

        config = overrides.get("config")
        if not isinstance(config, OpenAIJudgeConfig):
            config = OpenAIJudgeConfig.from_env(
                environ=environ,
                **_filter_config(overrides),
            )
        return OpenAIJudgeProvider(config=config)

    if key in {"gemini", "google", "google-gemini"}:
        from agent_eval_graders.providers.gemini.config import GeminiJudgeConfig
        from agent_eval_graders.providers.gemini.provider import GeminiJudgeProvider

        config = overrides.get("config")
        if not isinstance(config, GeminiJudgeConfig):
            config = GeminiJudgeConfig.from_env(
                environ=environ,
                **_filter_config(overrides),
            )
        return GeminiJudgeProvider(config=config)

    if key == "groq":
        from agent_eval_graders.providers.groq.config import GroqJudgeConfig
        from agent_eval_graders.providers.groq.provider import GroqJudgeProvider

        config = overrides.get("config")
        if not isinstance(config, GroqJudgeConfig):
            config = GroqJudgeConfig.from_env(
                environ=environ,
                **_filter_config(overrides),
            )
        return GroqJudgeProvider(config=config)

    raise ValueError(
        f"Unknown judge provider {name!r}; "
        "expected one of: anthropic, openai, gemini, groq, mock"
    )


def _filter_config(overrides: Mapping[str, object]) -> dict[str, object]:
    """Pass through known config constructor kwargs; drop provider-only keys."""
    allowed = {
        "api_key",
        "model",
        "timeout_seconds",
        "retry_count",
        "temperature",
        "seed",
        "max_tokens",
        "base_url",
    }
    return {k: v for k, v in overrides.items() if k in allowed and k != "config"}
