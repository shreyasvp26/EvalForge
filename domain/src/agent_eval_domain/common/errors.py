"""Typed domain errors.

Never retryable — retrying an invariant violation never helps.
"""

from __future__ import annotations

from typing import Any

from agent_eval_shared.errors import ApplicationError


class DomainError(ApplicationError):
    """Base for all Domain Layer failures."""

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


class InvariantViolation(DomainError):
    """A domain invariant would be broken by the attempted operation."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INVARIANT_VIOLATION",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class InvalidStateTransition(DomainError):
    """An entity lifecycle transition is not permitted from the current state."""

    def __init__(
        self,
        message: str,
        *,
        from_state: str,
        to_state: str,
        entity: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {"entity": entity, "from_state": from_state, "to_state": to_state}
        if details:
            payload.update(details)
        super().__init__(
            message,
            code="INVALID_STATE_TRANSITION",
            details=payload,
        )


class NotFoundError(DomainError):
    """A required domain entity or version could not be resolved."""

    def __init__(
        self,
        message: str,
        *,
        entity: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {"entity": entity, "entity_id": entity_id}
        if details:
            payload.update(details)
        super().__init__(message, code="NOT_FOUND", details=payload)
