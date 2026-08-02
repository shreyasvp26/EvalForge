"""Require non-blank string fields at the Application boundary."""

from __future__ import annotations

from agent_eval_application.errors import ApplicationValidationError


def require_non_empty(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationValidationError(
            f"{field} must be a non-empty string",
            code="INVALID_FIELD",
            details={"field": field},
        )
    return value.strip()
