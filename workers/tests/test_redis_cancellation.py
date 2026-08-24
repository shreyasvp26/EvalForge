"""Unit tests for RedisCancellationRegistry."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore
from agent_eval_workers.cancellation.redis_registry import RedisCancellationRegistry


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        del ex
        self.data[name] = value
        return True

    def exists(self, *names: str) -> int:
        return sum(1 for n in names if n in self.data)

    def delete(self, *names: str) -> int:
        removed = 0
        for n in names:
            if n in self.data:
                del self.data[n]
                removed += 1
        return removed


def test_redis_registry_merges_local_and_remote() -> None:
    store = RedisRunCancellationStore(_FakeRedis())
    registry = RedisCancellationRegistry(store)
    run_id = RunId("run-1")
    assert registry.is_cancel_requested(run_id) is False
    registry.request_cancel(run_id)
    assert registry.is_cancel_requested(run_id) is True
    # Remote-only signal (simulates API publish without local request).
    other = RedisCancellationRegistry(store)
    assert other.is_cancel_requested(run_id) is True
