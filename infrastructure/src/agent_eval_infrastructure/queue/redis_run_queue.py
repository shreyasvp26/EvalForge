"""Redis-compatible RunQueue adapter for the Application port.

Application only calls ``enqueue_run``. Claim / acknowledge methods exist for
Background Workers (Phase later) — this module contains no Worker logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_eval_domain.common.ids import RunId
from redis import Redis


class RedisClient(Protocol):
    """Subset of redis-py used by the queue (enables fakes in tests)."""

    def rpush(self, name: str, *values: str) -> int: ...

    def lmove(
        self,
        first_list: str,
        second_list: str,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None: ...

    def blmove(
        self,
        first_list: str,
        second_list: str,
        timeout: float,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None: ...

    def lrem(self, name: str, count: int, value: str) -> int: ...

    def lrange(self, name: str, start: int, end: int) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class ClaimedRun:
    """A Run task claimed from the queue (Worker-facing; not an Application DTO)."""

    run_id: RunId


class RedisRunQueue:
    """Reliable Redis list queue: pending → processing → ack/release.

    Keys (prefix configurable):
    - ``{prefix}:pending`` — waiting tasks
    - ``{prefix}:processing`` — claimed but not yet acknowledged
    """

    def __init__(
        self,
        client: RedisClient,
        *,
        key_prefix: str = "evalforge:runs",
        claim_timeout_seconds: float = 5.0,
    ) -> None:
        self._client = client
        self._pending = f"{key_prefix}:pending"
        self._processing = f"{key_prefix}:processing"
        self._claim_timeout_seconds = claim_timeout_seconds

    def enqueue_run(self, run_id: RunId) -> None:
        """Application ``RunQueue`` port — publish work for workers."""
        self._client.rpush(self._pending, run_id.value)

    def claim_run(self, *, block: bool = True) -> ClaimedRun | None:
        """Move one task from pending to processing (Worker hook)."""
        if block:
            try:
                raw = self._client.blmove(
                    self._pending,
                    self._processing,
                    self._claim_timeout_seconds,
                    src="LEFT",
                    dest="RIGHT",
                )
            except TimeoutError:
                # redis-py may surface idle BLMOVE waits as socket TimeoutError
                # when client socket_timeout ≈ block timeout. Treat as idle.
                return None
        else:
            raw = self._client.lmove(
                self._pending,
                self._processing,
                src="LEFT",
                dest="RIGHT",
            )
        if raw is None:
            return None
        return ClaimedRun(run_id=RunId(str(raw)))

    def acknowledge_run(self, run_id: RunId) -> None:
        """Remove a claimed task from processing after successful handling."""
        self._client.lrem(self._processing, 1, run_id.value)

    def release_run(self, run_id: RunId) -> None:
        """Return a claimed task to pending (retry / worker crash recovery)."""
        removed = self._client.lrem(self._processing, 1, run_id.value)
        if removed:
            self._client.rpush(self._pending, run_id.value)

    def dequeue_pending(self, run_id: RunId) -> bool:
        """Remove a not-yet-claimed run from pending (cancel-before-claim)."""
        removed = self._client.lrem(self._pending, 0, run_id.value)
        return bool(removed)

    def pending_run_ids(self) -> list[RunId]:
        """Introspection helper for tests / ops (not an Application API)."""
        return [RunId(v) for v in self._client.lrange(self._pending, 0, -1)]


def create_redis_client(redis_url: str) -> Redis:
    """Build a redis-py client from configuration (decode responses as str).

    ``socket_timeout`` is left ``None`` so blocking queue claims (BLMOVE) can
    wait for the full claim timeout without racing the client socket timer.
    """
    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=None,
        socket_connect_timeout=5.0,
    )
