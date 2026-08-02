"""Idempotency for use-case invocation.

Backend Architecture §8: Application enforces idempotency for use-case
invocation because the queue does not guarantee exactly-once delivery and
clients may safely retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class IdempotencyStatus(StrEnum):
    NEW = "new"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """Stored outcome for a previously completed idempotent operation."""

    key: str
    scope: str
    status: IdempotencyStatus
    result: dict[str, Any] | None = None


class IdempotencyStore(Protocol):
    """Tracks idempotency keys scoped to a use case / actor / resource."""

    def get(self, *, key: str, scope: str) -> IdempotencyRecord | None:
        """Return an existing record, or None if the key is unused."""

    def put_completed(
        self,
        *,
        key: str,
        scope: str,
        result: dict[str, Any],
    ) -> None:
        """Persist a completed outcome for safe replay."""
