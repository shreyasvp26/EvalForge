"""Sandbox-specific errors.

Sandbox failures are infrastructure failures (Backend Architecture §9): they
must never be conflated with an agent failing a case.
"""

from __future__ import annotations

from typing import Any

from agent_eval_shared.errors import InfrastructureError


class SandboxError(InfrastructureError):
    """Base error for all Sandbox Runtime failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "SANDBOX_ERROR",
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


class SandboxProvisionError(SandboxError):
    """Container create / start failed."""

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
            code="SANDBOX_PROVISION_FAILED",
            details=details,
            retryable=retryable,
            cause=cause,
        )


class SandboxStateError(SandboxError):
    """Illegal lifecycle operation for the current sandbox state."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_INVALID_STATE",
            details=details,
            retryable=False,
            cause=cause,
        )


class SandboxNotFoundError(SandboxError):
    """Sandbox handle is unknown to the manager / runtime."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_NOT_FOUND",
            details=details,
            retryable=False,
            cause=cause,
        )


class SandboxExecutionError(SandboxError):
    """Command execution failed at the infrastructure layer."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_EXECUTION_FAILED",
            details=details,
            retryable=retryable,
            cause=cause,
        )


class SandboxTimeoutError(SandboxError):
    """Execution exceeded the configured timeout."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_TIMEOUT",
            details=details,
            retryable=False,
            cause=cause,
        )


class SandboxCopyError(SandboxError):
    """Artifact / file copy_out failed."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_COPY_FAILED",
            details=details,
            retryable=False,
            cause=cause,
        )


class SandboxCleanupError(SandboxError):
    """Stop / destroy cleanup failed (best-effort still attempted)."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="SANDBOX_CLEANUP_FAILED",
            details=details,
            retryable=True,
            cause=cause,
        )
