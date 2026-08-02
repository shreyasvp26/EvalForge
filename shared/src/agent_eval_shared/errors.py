"""Typed error hierarchy for EvalForge (Backend Architecture §9)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Root error type. Prefer subclasses over raising this directly."""

    code: str
    details: dict[str, Any] | None
    retryable: bool

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details
        self.retryable = retryable
        if cause is not None:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": type(self).__name__,
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
        }
        if self.details is not None:
            payload["details"] = self.details
        if self.__cause__ is not None:
            payload["cause"] = serialize_error(self.__cause__)
        return payload


class ApplicationError(AppError):
    """Expected application/use-case failure. Not retryable by default."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
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


class InfrastructureError(AppError):
    """Infrastructure failure. Set retryable=True for transient failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
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


class ValidationError(AppError):
    """Input or semantic validation failure. Never retryable."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            details=details,
            retryable=False,
            cause=cause,
        )


class ConfigurationError(AppError):
    """Invalid or missing configuration at startup. Fail fast."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INVALID_CONFIGURATION",
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            details=details,
            retryable=False,
            cause=cause,
        )


def serialize_error(error: BaseException) -> dict[str, Any]:
    """Serialize any exception into a structured, JSON-friendly dict."""
    if isinstance(error, AppError):
        return error.to_dict()
    return {
        "name": type(error).__name__,
        "code": "UNTYPED_ERROR",
        "message": str(error),
        "retryable": False,
    }
