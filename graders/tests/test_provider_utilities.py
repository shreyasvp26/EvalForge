"""Unit tests for shared judge-provider utilities (no vendor HTTP)."""

from __future__ import annotations

import pytest
from agent_eval_graders.providers import (
    JudgeAuthenticationError,
    JudgeInvalidResponseError,
    JudgeRateLimitError,
    JudgeTimeout,
    ProviderConfig,
    call_with_retry,
    create_judge_provider,
    effective_settings,
    exponential_delay_seconds,
    is_retryable_provider_error,
    normalize_provider_name,
    require_api_key,
    resolve_model,
    resolve_seed,
    resolve_temperature,
)
from agent_eval_graders.providers.config import load_common_knobs
from agent_eval_graders.providers.http import map_http_status
from agent_eval_graders.rubric.models import DeterminismControls


def test_exponential_delay_doubles_and_caps() -> None:
    assert exponential_delay_seconds(0, base_seconds=0.5, max_seconds=8.0) == 0.5
    assert exponential_delay_seconds(1, base_seconds=0.5, max_seconds=8.0) == 1.0
    assert exponential_delay_seconds(2, base_seconds=0.5, max_seconds=8.0) == 2.0
    assert exponential_delay_seconds(10, base_seconds=0.5, max_seconds=8.0) == 8.0


def test_call_with_retry_retries_rate_limit_then_succeeds() -> None:
    sleeps: list[float] = []
    state = {"n": 0}

    def operation() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise JudgeRateLimitError("limited")
        return "ok"

    result = call_with_retry(
        operation,
        retry_count=3,
        base_seconds=0.1,
        sleep=sleeps.append,
    )
    assert result == "ok"
    assert state["n"] == 3
    assert sleeps == [0.1, 0.2]


def test_call_with_retry_does_not_retry_auth() -> None:
    calls = {"n": 0}

    def operation() -> None:
        calls["n"] += 1
        raise JudgeAuthenticationError("bad key")

    with pytest.raises(JudgeAuthenticationError):
        call_with_retry(operation, retry_count=5, sleep=lambda _d: None)
    assert calls["n"] == 1


def test_call_with_retry_does_not_retry_invalid_response() -> None:
    def operation() -> None:
        raise JudgeInvalidResponseError("bad payload")

    with pytest.raises(JudgeInvalidResponseError):
        call_with_retry(operation, retry_count=5, sleep=lambda _d: None)


def test_map_http_status_classes() -> None:
    map_http_status(200, provider="x")  # no raise
    with pytest.raises(JudgeAuthenticationError):
        map_http_status(401, provider="x")
    with pytest.raises(JudgeRateLimitError):
        map_http_status(429, provider="x")
    with pytest.raises(JudgeTimeout):
        map_http_status(504, provider="x")
    with pytest.raises(JudgeInvalidResponseError):
        map_http_status(400, provider="x")


def test_is_retryable_flags() -> None:
    assert is_retryable_provider_error(JudgeRateLimitError("x"))
    assert not is_retryable_provider_error(JudgeAuthenticationError("x"))
    assert not is_retryable_provider_error(JudgeInvalidResponseError("x"))
    assert not is_retryable_provider_error(ValueError("x"))


def test_require_api_key_and_common_knobs() -> None:
    assert require_api_key("K", environ={"K": "secret"}) == "secret"
    with pytest.raises(ValueError, match="Missing required API key"):
        require_api_key("K", environ={})

    knobs = load_common_knobs(
        environ={
            "JUDGE_TIMEOUT_SECONDS": "12.5",
            "JUDGE_RETRY_COUNT": "4",
            "JUDGE_TEMPERATURE": "0.1",
            "JUDGE_SEED": "none",
            "JUDGE_MAX_TOKENS": "100",
        },
        prefix="JUDGE",
    )
    assert knobs["timeout_seconds"] == 12.5
    assert knobs["retry_count"] == 4
    assert knobs["temperature"] == 0.1
    assert knobs["seed"] is None
    assert knobs["max_tokens"] == 100


def test_provider_config_validation() -> None:
    cfg = ProviderConfig(api_key="k", model="m")
    assert cfg.retry_count == 2
    with pytest.raises(ValueError):
        ProviderConfig(api_key="", model="m")


def test_determinism_resolvers() -> None:
    cfg = ProviderConfig(api_key="k", model="claude-default", temperature=0.2, seed=9)
    controls = DeterminismControls(temperature=0.0, seed=42, model_hint="claude-pinned")
    assert resolve_model(controls, cfg) == "claude-pinned"
    assert resolve_model(DeterminismControls(), cfg) == "claude-default"
    assert resolve_temperature(controls, cfg) == 0.0
    assert resolve_seed(controls, cfg) == 42
    settings = effective_settings(
        provider="anthropic",
        model="claude-pinned",
        temperature=0.0,
        seed=42,
        seed_supported=False,
        max_tokens=2048,
        model_hint="claude-pinned",
    )
    assert settings["seed"] is None
    assert settings["seed_supported"] is False


def test_create_judge_provider_mock_and_unknown() -> None:
    assert normalize_provider_name("Open_AI") == "open-ai"
    body = '{"numeric": 1, "passed": true, "reason": "ok"}'
    provider = create_judge_provider("mock", response=body)
    assert provider.complete  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match="Unknown judge provider"):
        create_judge_provider("nope")
