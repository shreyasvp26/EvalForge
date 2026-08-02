"""Adapter-layer errors.

Adapter failures are distinct from Agent-signaled failure to solve a case
(Adapter Architecture — Failure Model).
"""

from __future__ import annotations

from typing import Any

from agent_eval_shared.errors import InfrastructureError


class AdapterError(InfrastructureError):
    """Base error for Adapter SDK / vendor adapter failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "ADAPTER_ERROR",
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


class AdapterInitializationError(AdapterError):
    """initialize/prepare failed before Agent execution began."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="ADAPTER_INIT_FAILED",
            details=details,
            retryable=retryable,
            cause=cause,
        )


class AdapterTranslationError(AdapterError):
    """Observed output could not be mapped onto the NDM."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="ADAPTER_TRANSLATION_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class MalformedOutputError(AdapterTranslationError):
    """Native agent stream was malformed / unparseable."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        AdapterError.__init__(
            self,
            message,
            code="ADAPTER_MALFORMED_OUTPUT",
            details=details,
            retryable=False,
            cause=cause,
        )


class AdapterCancellationError(AdapterError):
    """Cooperative cancellation requested during adapter invocation."""

    def __init__(
        self,
        message: str = "Adapter invocation cancelled",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="ADAPTER_CANCELLED",
            details=details,
            retryable=False,
            cause=cause,
        )


class AdapterTimeoutError(AdapterError):
    """Adapter / agent stream exceeded the configured timeout."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="ADAPTER_TIMEOUT",
            details=details,
            retryable=False,
            cause=cause,
        )
