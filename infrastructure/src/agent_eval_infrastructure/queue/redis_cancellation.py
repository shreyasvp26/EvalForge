"""Redis-backed run cancellation signals (API publish → worker observe)."""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import RunId


class RedisCancelClient(Protocol):
    def set(self, name: str, value: str, ex: int | None = None) -> object: ...

    def exists(self, *names: str) -> int: ...

    def delete(self, *names: str) -> int: ...


class RedisRunCancellationStore:
    """Shared cancel intent store — API writes, workers read.

    Keys expire so abandoned signals do not accumulate forever.
    """

    def __init__(
        self,
        client: RedisCancelClient,
        *,
        key_prefix: str = "evalforge:cancel",
        ttl_seconds: int = 86_400,
    ) -> None:
        self._client = client
        self._key_prefix = key_prefix.rstrip(":")
        self._ttl_seconds = ttl_seconds

    def request_cancel(self, run_id: RunId | str) -> None:
        key = self._key(run_id)
        self._client.set(key, "1", ex=self._ttl_seconds)

    def is_cancel_requested(self, run_id: RunId | str) -> bool:
        return bool(self._client.exists(self._key(run_id)))

    def clear(self, run_id: RunId | str) -> None:
        self._client.delete(self._key(run_id))

    def _key(self, run_id: RunId | str) -> str:
        value = run_id.value if isinstance(run_id, RunId) else run_id
        return f"{self._key_prefix}:{value}"
