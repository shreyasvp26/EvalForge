"""Redis-backed idempotency store for Application use-case invocation."""

from __future__ import annotations

import json
from typing import Any, Protocol

from agent_eval_application.ports.idempotency import (
    IdempotencyRecord,
    IdempotencyStatus,
)


class RedisHashClient(Protocol):
    def hget(self, name: str, key: str) -> str | None: ...

    def hset(self, name: str, key: str, value: str) -> int: ...


class RedisIdempotencyStore:
    """Stores completed idempotency outcomes in a Redis hash."""

    def __init__(
        self,
        client: RedisHashClient,
        *,
        key_prefix: str = "evalforge:idempotency",
    ) -> None:
        self._client = client
        self._key_prefix = key_prefix

    def get(self, *, key: str, scope: str) -> IdempotencyRecord | None:
        raw = self._client.hget(self._bucket(scope), key)
        if raw is None:
            return None
        payload = json.loads(raw)
        return IdempotencyRecord(
            key=key,
            scope=scope,
            status=IdempotencyStatus(payload["status"]),
            result=payload.get("result"),
        )

    def put_completed(
        self,
        *,
        key: str,
        scope: str,
        result: dict[str, Any],
    ) -> None:
        payload = {
            "status": IdempotencyStatus.COMPLETED.value,
            "result": result,
        }
        self._client.hset(self._bucket(scope), key, json.dumps(payload))

    def _bucket(self, scope: str) -> str:
        return f"{self._key_prefix}:{scope}"
