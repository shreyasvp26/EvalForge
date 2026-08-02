"""Rubric-family errors (Grader Architecture — Failure Model)."""

from __future__ import annotations

from typing import Any

from agent_eval_graders.sdk.exceptions import (
    GraderError,
    GraderJudgmentError,
    GraderTimeoutError,
)


class RubricError(GraderError):
    """Base error for the rubric grading family."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "RUBRIC_ERROR",
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            details=details,
            retryable=retryable,
            cause=cause,
        )


class RubricParseError(GraderJudgmentError):
    """Malformed / schema-invalid judge response — not retryable."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        GraderError.__init__(
            self,
            message,
            code="RUBRIC_PARSE_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class RubricSchemaError(RubricParseError):
    """Judge response failed strict schema validation."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        GraderError.__init__(
            self,
            message,
            code="RUBRIC_SCHEMA_MISMATCH",
            details=details,
            retryable=False,
            cause=cause,
        )


class JudgeProviderUnavailable(RubricError):
    """Transient provider outage — retryable infrastructure failure."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="JUDGE_PROVIDER_UNAVAILABLE",
            details=details,
            retryable=True,
            cause=cause,
        )


class JudgeTimeout(GraderTimeoutError):
    """Judge invocation exceeded timeout — retryable."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        GraderError.__init__(
            self,
            message,
            code="JUDGE_TIMEOUT",
            details=details,
            retryable=True,
            cause=cause,
        )


class RubricPromptError(GraderJudgmentError):
    """Prompt construction failed (judgment failure, not retryable)."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        GraderError.__init__(
            self,
            message,
            code="RUBRIC_PROMPT_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )
