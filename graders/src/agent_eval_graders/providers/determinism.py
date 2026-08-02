"""Determinism helpers shared by production judge providers."""

from __future__ import annotations

from typing import Any, Protocol

from agent_eval_graders.rubric.models import DeterminismControls

_MOCK_MODEL_HINT = "mock-judge"


class JudgeSamplingConfig(Protocol):
    """Minimal config surface needed to resolve determinism controls."""

    model: str
    temperature: float
    seed: int | None
    max_tokens: int


def resolve_model(controls: DeterminismControls, config: JudgeSamplingConfig) -> str:
    """Prefer a real model hint; fall back to provider default."""
    hint = (controls.model_hint or "").strip()
    if not hint or hint == _MOCK_MODEL_HINT:
        return config.model
    return hint


def resolve_temperature(
    controls: DeterminismControls,
    config: JudgeSamplingConfig,
) -> float:
    """Honor DeterminismControls.temperature (config is fallback only)."""
    if controls.temperature is not None:
        return float(controls.temperature)
    return float(config.temperature)


def resolve_seed(
    controls: DeterminismControls,
    config: JudgeSamplingConfig,
) -> int | None:
    """Prefer controls.seed when set; otherwise provider config seed."""
    if controls.seed is not None:
        return controls.seed
    return config.seed


def resolve_max_tokens(
    controls: DeterminismControls,
    config: JudgeSamplingConfig,
) -> int:
    return int(controls.max_tokens if controls.max_tokens else config.max_tokens)


def effective_settings(
    *,
    provider: str,
    model: str,
    temperature: float,
    seed: int | None,
    seed_supported: bool,
    max_tokens: int,
    model_hint: str,
) -> dict[str, Any]:
    """Settings recorded on ``JudgeRawResponse.metadata`` / Score detail."""
    return {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "seed": seed if seed_supported else None,
        "seed_supported": seed_supported,
        "max_tokens": max_tokens,
        "model_hint": model_hint,
    }
