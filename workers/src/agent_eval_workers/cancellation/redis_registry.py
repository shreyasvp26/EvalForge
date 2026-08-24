"""Redis-backed cancellation registry for multi-process workers."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore

from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry


class RedisCancellationRegistry:
    """``CancellationPort`` (+ request/clear) backed by Redis.

    Optionally merges a local in-memory registry so in-process test hooks and
    cooperative adapter cancels still work without a round-trip.
    """

    def __init__(
        self,
        store: RedisRunCancellationStore,
        *,
        local: InMemoryCancellationRegistry | None = None,
    ) -> None:
        self._store = store
        self._local = local or InMemoryCancellationRegistry()

    def request_cancel(self, run_id: RunId) -> None:
        self._local.request_cancel(run_id)
        self._store.request_cancel(run_id)

    def clear(self, run_id: RunId) -> None:
        self._local.clear(run_id)
        self._store.clear(run_id)

    def is_cancel_requested(self, run_id: RunId) -> bool:
        if self._local.is_cancel_requested(run_id):
            return True
        return self._store.is_cancel_requested(run_id)
