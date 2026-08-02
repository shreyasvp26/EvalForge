"""Grader-layer errors (Grader Architecture — Failure Model)."""

from __future__ import annotations

from typing import Any

from agent_eval_shared.errors import InfrastructureError


class GraderError(InfrastructureError):
    """Base error for Grader SDK / grader failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GRADER_ERROR",
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


class GraderInitializationError(GraderError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="GRADER_INIT_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class GraderJudgmentError(GraderError):
    """Judgment failure — not retried automatically."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="GRADER_JUDGMENT_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class GraderTimeoutError(GraderError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="GRADER_TIMEOUT",
            details=details,
            retryable=True,
            cause=cause,
        )


class DuplicateScoreError(GraderError):
    """Exactly one Score per Run × Grader Version (Domain Invariant 2)."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="DUPLICATE_SCORE",
            details=details,
            retryable=False,
            cause=cause,
        )
