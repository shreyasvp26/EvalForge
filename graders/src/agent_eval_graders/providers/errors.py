"""Platform judge-provider failures — never leak vendor exceptions."""

from __future__ import annotations

from typing import Any

from agent_eval_graders.rubric.exceptions import (
    JudgeProviderUnavailable,
    JudgeTimeout,
    RubricError,
)
from agent_eval_graders.sdk.exceptions import GraderError


class JudgeAuthenticationError(RubricError):
    """Missing / invalid API credentials — not retryable."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="JUDGE_AUTHENTICATION_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class JudgeRateLimitError(RubricError):
    """Provider rate limit (HTTP 429) — retryable with backoff."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="JUDGE_RATE_LIMITED",
            details=details,
            retryable=True,
            cause=cause,
        )


class JudgeNetworkError(RubricError):
    """Transport / connectivity failure — retryable."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="JUDGE_NETWORK_ERROR",
            details=details,
            retryable=True,
            cause=cause,
        )


class JudgeInvalidResponseError(RubricError):
    """Vendor HTTP/API payload unusable — not retryable.

    Distinct from rubric JSON schema failures (``RubricParseError``), which
    occur after a successful provider completion returns content.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="JUDGE_INVALID_RESPONSE",
            details=details,
            retryable=False,
            cause=cause,
        )


def is_retryable_provider_error(exc: BaseException) -> bool:
    """Whether a mapped provider failure should be retried with backoff."""
    if isinstance(exc, GraderError):
        return bool(exc.retryable)
    return False


__all__ = [
    "JudgeAuthenticationError",
    "JudgeInvalidResponseError",
    "JudgeNetworkError",
    "JudgeProviderUnavailable",
    "JudgeRateLimitError",
    "JudgeTimeout",
    "is_retryable_provider_error",
]
