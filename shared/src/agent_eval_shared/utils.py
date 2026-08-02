"""Small cross-cutting utilities. Keep this module intentionally boring."""

from __future__ import annotations

import uuid
from typing import NoReturn, TypeGuard


def create_correlation_id() -> str:
    """Generate a correlation ID for request/run tracing across processes."""
    return str(uuid.uuid4())


def invariant(condition: object, message: str = "Invariant violated") -> None:
    """Assert an invariant. Raises AssertionError on failure."""
    if not condition:
        raise AssertionError(message)


def is_non_empty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def assert_never(value: object) -> NoReturn:
    raise AssertionError(f"Unexpected value: {value!r}")
