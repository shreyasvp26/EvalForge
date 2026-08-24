"""Unit tests for Redis cancel signal store."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self.data[name] = value
        self.ttls[name] = ex
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


def test_redis_cancel_request_observe_clear() -> None:
    client = _FakeRedis()
    store = RedisRunCancellationStore(
        client,
        key_prefix="evalforge:cancel",
        ttl_seconds=60,
    )
    run_id = RunId("run-abc")
    assert store.is_cancel_requested(run_id) is False
    store.request_cancel(run_id)
    assert store.is_cancel_requested(run_id) is True
    assert client.ttls["evalforge:cancel:run-abc"] == 60
    store.clear(run_id)
    assert store.is_cancel_requested(run_id) is False
