"""Production judge provider integration tests — mocked HTTP only."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from agent_eval_graders.providers import (
    JudgeAuthenticationError,
    JudgeInvalidResponseError,
    JudgeProviderUnavailable,
    JudgeRateLimitError,
    JudgeTimeout,
    create_judge_provider,
)
from agent_eval_graders.providers.anthropic import (
    AnthropicJudgeConfig,
    AnthropicJudgeProvider,
)
from agent_eval_graders.providers.gemini import GeminiJudgeConfig, GeminiJudgeProvider
from agent_eval_graders.providers.groq import GroqJudgeConfig, GroqJudgeProvider
from agent_eval_graders.providers.openai import OpenAIJudgeConfig, OpenAIJudgeProvider
from agent_eval_graders.rubric.models import (
    DeterminismControls,
    JudgePrompt,
    JudgeRequest,
)

JUDGE_JSON = json.dumps(
    {"numeric": 0.9, "passed": True, "reason": "Looks correct"},
)


def _prompt() -> JudgePrompt:
    return JudgePrompt(
        system="You are a rubric judge. Reply with JSON only.",
        user="Grade this run.",
        grader_version_id="gv-1",
        rubric_fingerprint="abc123",
    )


def _request(
    *,
    temperature: float = 0.0,
    seed: int | None = 42,
    model_hint: str = "mock-judge",
    timeout_seconds: float = 5.0,
) -> JudgeRequest:
    return JudgeRequest(
        prompt=_prompt(),
        controls=DeterminismControls(
            temperature=temperature,
            seed=seed,
            model_hint=model_hint,
            max_tokens=256,
        ),
        timeout_seconds=timeout_seconds,
        correlation_id="corr-judge",
    )


def _transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


def _anthropic_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    assert body["temperature"] == 0.0
    assert "seed" not in body
    assert body["model"] == "claude-test"
    return httpx.Response(
        200,
        json={
            "id": "msg_1",
            "model": "claude-test",
            "content": [{"type": "text", "text": JUDGE_JSON}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        },
    )


def test_anthropic_successful_completion() -> None:
    client = httpx.Client(transport=_transport(_anthropic_ok))
    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="sk-ant", model="claude-default"),
        http_client=client,
    )
    raw = provider.complete(_request(model_hint="claude-test"))
    assert json.loads(raw.content)["passed"] is True
    assert raw.model == "claude-test"
    assert raw.metadata["provider"] == "anthropic"
    assert raw.metadata["temperature"] == 0.0
    assert raw.metadata["seed_supported"] is False
    assert raw.metadata["seed"] is None


def test_anthropic_authentication_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="bad", retry_count=2),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeAuthenticationError) as exc:
        provider.complete(_request())
    assert exc.value.retryable is False


def test_anthropic_rate_limit_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="rate limited")
        return _anthropic_ok(request)

    monkeypatch.setattr(
        "agent_eval_graders.providers.retry.time.sleep",
        sleeps.append,
    )
    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="k", model="claude-test", retry_count=3),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    raw = provider.complete(_request(model_hint="claude-test"))
    assert raw.metadata["provider"] == "anthropic"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_anthropic_timeout() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeTimeout) as exc:
        provider.complete(_request())
    assert exc.value.retryable is True


def test_anthropic_malformed_json_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="{not-json")

    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeInvalidResponseError) as exc:
        provider.complete(_request())
    assert exc.value.retryable is False


def test_anthropic_provider_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeProviderUnavailable) as exc:
        provider.complete(_request())
    assert exc.value.retryable is True


def test_anthropic_config_from_env() -> None:
    cfg = AnthropicJudgeConfig.from_env(
        environ={
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "ANTHROPIC_MODEL": "claude-env",
            "ANTHROPIC_TIMEOUT_SECONDS": "15",
            "ANTHROPIC_RETRY_COUNT": "1",
            "ANTHROPIC_TEMPERATURE": "0.0",
            "ANTHROPIC_SEED": "7",
        }
    )
    assert cfg.api_key == "sk-ant-test"
    assert cfg.model == "claude-env"
    assert cfg.timeout_seconds == 15.0
    assert cfg.retry_count == 1
    assert cfg.seed == 7


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


def _openai_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    assert body["temperature"] == 0.0
    assert body["seed"] == 99
    assert body["model"] == "gpt-test"
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl_1",
            "model": "gpt-test",
            "choices": [
                {
                    "message": {"role": "assistant", "content": JUDGE_JSON},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        },
    )


def test_openai_successful_completion_and_determinism() -> None:
    provider = OpenAIJudgeProvider(
        config=OpenAIJudgeConfig(api_key="sk-openai", model="gpt-default"),
        http_client=httpx.Client(transport=_transport(_openai_ok)),
    )
    raw = provider.complete(_request(seed=99, model_hint="gpt-test"))
    assert raw.model == "gpt-test"
    assert raw.metadata["provider"] == "openai"
    assert raw.metadata["seed"] == 99
    assert raw.metadata["seed_supported"] is True
    assert raw.metadata["temperature"] == 0.0


def test_openai_rate_limit_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down")

    monkeypatch.setattr(
        "agent_eval_graders.providers.retry.time.sleep",
        lambda _d: None,
    )
    provider = OpenAIJudgeProvider(
        config=OpenAIJudgeConfig(api_key="k", retry_count=2),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeRateLimitError) as exc:
        provider.complete(_request())
    assert exc.value.retryable is True


def test_openai_auth_and_malformed() -> None:
    def auth(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    provider = OpenAIJudgeProvider(
        config=OpenAIJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(auth)),
    )
    with pytest.raises(JudgeAuthenticationError):
        provider.complete(_request())

    def empty_choices(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = OpenAIJudgeProvider(
        config=OpenAIJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(empty_choices)),
    )
    with pytest.raises(JudgeInvalidResponseError):
        provider.complete(_request())


def test_openai_config_from_env() -> None:
    cfg = OpenAIJudgeConfig.from_env(
        environ={
            "OPENAI_API_KEY": "sk-openai",
            "OPENAI_MODEL": "gpt-env",
            "OPENAI_RETRY_COUNT": "3",
        }
    )
    assert cfg.model == "gpt-env"
    assert cfg.retry_count == 3


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def _gemini_ok(request: httpx.Request) -> httpx.Response:
    assert "key=" in str(request.url)
    body = json.loads(request.content.decode())
    gen = body["generationConfig"]
    assert gen["temperature"] == 0.0
    assert gen["seed"] == 7
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {"parts": [{"text": JUDGE_JSON}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 1},
            "modelVersion": "gemini-test",
        },
    )


def test_gemini_successful_completion_and_determinism() -> None:
    provider = GeminiJudgeProvider(
        config=GeminiJudgeConfig(api_key="gem-key", model="gemini-test"),
        http_client=httpx.Client(transport=_transport(_gemini_ok)),
    )
    raw = provider.complete(_request(seed=7, model_hint="gemini-test"))
    assert json.loads(raw.content)["numeric"] == 0.9
    assert raw.metadata["provider"] == "gemini"
    assert raw.metadata["seed"] == 7
    assert raw.metadata["seed_supported"] is True


def test_gemini_unavailable_and_timeout() -> None:
    def unavailable(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    provider = GeminiJudgeProvider(
        config=GeminiJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(unavailable)),
    )
    with pytest.raises(JudgeProviderUnavailable):
        provider.complete(_request())

    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("no route")

    provider = GeminiJudgeProvider(
        config=GeminiJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(timeout)),
    )
    with pytest.raises(JudgeTimeout):
        provider.complete(_request())


def test_gemini_malformed_candidates() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    provider = GeminiJudgeProvider(
        config=GeminiJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(JudgeInvalidResponseError):
        provider.complete(_request())


def test_gemini_config_from_env() -> None:
    cfg = GeminiJudgeConfig.from_env(
        environ={
            "GEMINI_API_KEY": "gem-key",
            "GEMINI_MODEL": "gemini-env",
            "GEMINI_SEED": "none",
        }
    )
    assert cfg.model == "gemini-env"
    assert cfg.seed is None


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def test_provider_selection_builds_each_vendor() -> None:
    anthropic = create_judge_provider(
        "anthropic",
        config=AnthropicJudgeConfig(api_key="k"),
    )
    openai = create_judge_provider(
        "openai",
        config=OpenAIJudgeConfig(api_key="k"),
    )
    gemini = create_judge_provider(
        "gemini",
        config=GeminiJudgeConfig(api_key="k"),
    )
    groq = create_judge_provider(
        "groq",
        config=GroqJudgeConfig(api_key="k"),
    )
    assert isinstance(anthropic, AnthropicJudgeProvider)
    assert isinstance(openai, OpenAIJudgeProvider)
    assert isinstance(gemini, GeminiJudgeProvider)
    assert isinstance(groq, GroqJudgeProvider)


def _groq_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    assert body["model"] == "llama-test"
    assert body["temperature"] == 0.0
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-g",
            "model": "llama-test",
            "choices": [
                {
                    "message": {"role": "assistant", "content": JUDGE_JSON},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        },
    )


def test_groq_provider_completes_with_structured_json() -> None:
    provider = GroqJudgeProvider(
        config=GroqJudgeConfig(api_key="k", model="llama-test", retry_count=0),
        http_client=httpx.Client(transport=_transport(_groq_ok)),
    )
    raw = provider.complete(_request(model_hint="llama-test"))
    assert json.loads(raw.content)["passed"] is True
    assert raw.model == "llama-test"
    assert raw.metadata["provider"] == "groq"


def test_groq_config_requires_api_key() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqJudgeConfig.from_env(environ={})


def test_groq_config_accepts_graq_alias() -> None:
    config = GroqJudgeConfig.from_env(environ={"GRAQ_API_KEY": "alias-key"})
    assert config.api_key == "alias-key"


def test_provider_selection_from_env_keys() -> None:
    provider = create_judge_provider(
        "anthropic",
        environ={"ANTHROPIC_API_KEY": "sk-from-env", "ANTHROPIC_MODEL": "claude-x"},
    )
    assert isinstance(provider, AnthropicJudgeProvider)
    assert provider.config.api_key == "sk-from-env"
    assert provider.config.model == "claude-x"


def test_no_vendor_exception_leaks_on_network_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.NetworkError("dns failed")

    provider = OpenAIJudgeProvider(
        config=OpenAIJudgeConfig(api_key="k", retry_count=0),
        http_client=httpx.Client(transport=_transport(handler)),
    )
    with pytest.raises(Exception) as exc:
        provider.complete(_request())
    assert not isinstance(exc.value, httpx.HTTPError)
    from agent_eval_graders.providers.errors import JudgeNetworkError

    assert isinstance(exc.value, JudgeNetworkError)


def test_rubric_grader_still_works_with_anthropic_provider() -> None:
    """Providers plug into RubricGrader without lifecycle changes."""
    from agent_eval_domain.common.ids import GraderId, GraderVersionId
    from agent_eval_graders.rubric import RubricGrader, RubricSpecification
    from agent_eval_graders.sdk import GradingConfig, GradingContext, run_grader
    from grader_fakes import CollectingSink, InMemoryRunReader

    provider = AnthropicJudgeProvider(
        config=AnthropicJudgeConfig(api_key="k", model="claude-test", retry_count=0),
        http_client=httpx.Client(transport=_transport(_anthropic_ok)),
    )
    rubric = RubricSpecification(
        title="Quality",
        instructions="Score the change.",
        pass_threshold=0.5,
    )
    grader = RubricGrader(rubric=rubric, provider=provider)
    reader = InMemoryRunReader()
    reader.add_edit("main.py", "@@\n+print('hi')\n")
    ctx = GradingContext(
        reader=reader,
        grader_id=GraderId("grader-rubric"),
        grader_version_id=GraderVersionId("gv-1"),
        grader_version_label="v1",
        grader_specification=rubric.instructions,
        correlation_id="corr",
        config=GradingConfig(timeout_seconds=30.0),
    )
    sink = CollectingSink()
    outcome = run_grader(grader, ctx, sink)
    assert outcome.outcome.name == "SUCCEEDED"
    assert len(sink.scores) == 1
    assert sink.scores[0].value.detail.get("family") == "rubric"
