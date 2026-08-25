"""Unit tests for Gemini CLI failure classification."""

from __future__ import annotations

from agent_eval_adapters.gemini.errors import classify_gemini_cli_failure


def test_classify_rate_limit_from_quota_message() -> None:
    reason = classify_gemini_cli_failure(
        stderr="cause: { code: 429, message: 'You exceeded your current quota' }",
        stdout="",
        exit_code=173,
    )
    assert reason == "Gemini API rate limit exceeded"


def test_classify_rate_limit_from_result_json() -> None:
    stdout = (
        '{"type":"result","status":"error","error":{"message":'
        '"[API Error: You have exhausted your daily quota on this model.]"}}'
    )
    reason = classify_gemini_cli_failure(stderr="", stdout=stdout, exit_code=0)
    assert reason == "Gemini API rate limit exceeded"


def test_classify_auth_failure() -> None:
    reason = classify_gemini_cli_failure(
        stderr="API key not valid. Please pass a valid API key.",
        stdout="",
        exit_code=1,
    )
    assert reason == "Gemini authentication failed"


def test_classify_benign_stderr_with_success_is_none() -> None:
    reason = classify_gemini_cli_failure(
        stderr=(
            "YOLO mode is enabled. All tool calls will be automatically approved.\n"
            "Ripgrep is not available. Falling back to GrepTool.\n"
        ),
        stdout='{"type":"result","status":"success"}',
        exit_code=0,
    )
    assert reason is None


def test_classify_nonzero_exit_without_known_pattern() -> None:
    reason = classify_gemini_cli_failure(
        stderr="something exploded in the runtime",
        stdout="",
        exit_code=2,
    )
    assert reason is not None
    assert "exit 2" in reason
    assert "something exploded" in reason
