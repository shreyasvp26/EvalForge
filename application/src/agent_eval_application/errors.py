"""Application-layer errors and Domain error translation.

Backend Architecture §9: Domain errors are typed, never retryable, and must be
caught/translated by Application before reaching API or Workers as a meaningful
failure. Infrastructure errors remain distinct and may be retryable.
"""

from __future__ import annotations

from typing import Any

from agent_eval_domain.common.errors import DomainError, NotFoundError
from agent_eval_shared.errors import ApplicationError, ValidationError


class ApplicationLayerError(ApplicationError):
    """Base for Application Layer orchestration failures."""

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


class AuthorizationError(ApplicationLayerError):
    """Caller is authenticated but not permitted for this operation."""

    def __init__(
        self,
        message: str = "Not authorized for this operation",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code="FORBIDDEN",
            details=details,
            cause=cause,
        )


class NotFoundApplicationError(ApplicationLayerError):
    """A required resource could not be resolved for this use case."""

    def __init__(
        self,
        message: str,
        *,
        entity: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        payload = {"entity": entity, "entity_id": entity_id}
        if details:
            payload.update(details)
        super().__init__(
            message,
            code="NOT_FOUND",
            details=payload,
            cause=cause,
        )


class ConflictError(ApplicationLayerError):
    """Use-case conflict (duplicate idempotency key outcome mismatch, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details, cause=cause)


class DomainTranslationError(ApplicationLayerError):
    """A Domain invariant/state failure translated for Application callers."""

    def __init__(self, domain_error: DomainError) -> None:
        super().__init__(
            str(domain_error),
            code=domain_error.code,
            details=domain_error.details,
            cause=domain_error,
        )


class ApplicationValidationError(ValidationError):
    """Semantic validation failure at the Application boundary."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APPLICATION_VALIDATION",
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details, cause=cause)


def translate_domain_error(error: DomainError) -> ApplicationLayerError:
    """Map a Domain error to an Application-layer error for callers."""
    if isinstance(error, NotFoundError):
        entity = (error.details or {}).get("entity", "Unknown")
        entity_id = (error.details or {}).get("entity_id", "")
        return NotFoundApplicationError(
            str(error),
            entity=str(entity),
            entity_id=str(entity_id),
            details=error.details,
            cause=error,
        )
    return DomainTranslationError(error)


def reraise_as_application(error: BaseException) -> None:
    """Re-raise Domain errors as Application errors; leave others untouched."""
    if isinstance(error, DomainError):
        raise translate_domain_error(error) from error
    raise error
