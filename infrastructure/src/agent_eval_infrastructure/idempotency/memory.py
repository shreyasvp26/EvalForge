"""In-memory idempotency store for tests / local composition."""

from __future__ import annotations

from typing import Any

from agent_eval_application.ports.idempotency import (
    IdempotencyRecord,
    IdempotencyStatus,
)


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdempotencyRecord] = {}

    def get(self, *, key: str, scope: str) -> IdempotencyRecord | None:
        return self._records.get((key, scope))

    def put_completed(
        self,
        *,
        key: str,
        scope: str,
        result: dict[str, Any],
    ) -> None:
        self._records[(key, scope)] = IdempotencyRecord(
            key=key,
            scope=scope,
            status=IdempotencyStatus.COMPLETED,
            result=result,
        )
