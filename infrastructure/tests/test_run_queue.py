"""Run queue adapter tests (in-memory + FakeRedis)."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue import InMemoryRunQueue, RedisRunQueue

from .fakes import FakeRedis


def test_in_memory_enqueue_claim_ack() -> None:
    queue = InMemoryRunQueue()
    queue.enqueue_run(RunId("run-1"))
    queue.enqueue_run(RunId("run-2"))
    assert [r.value for r in queue.pending_run_ids()] == ["run-1", "run-2"]

    claimed = queue.claim_run(block=False)
    assert claimed is not None
    assert claimed.run_id.value == "run-1"
    queue.acknowledge_run(claimed.run_id)
    assert queue.claim_run(block=False) is not None


def test_in_memory_release_returns_to_pending() -> None:
    queue = InMemoryRunQueue()
    queue.enqueue_run(RunId("run-1"))
    claimed = queue.claim_run(block=False)
    assert claimed is not None
    queue.release_run(claimed.run_id)
    again = queue.claim_run(block=False)
    assert again is not None
    assert again.run_id.value == "run-1"


def test_redis_run_queue_enqueue_claim_ack() -> None:
    client = FakeRedis()
    queue = RedisRunQueue(client, key_prefix="test:runs", claim_timeout_seconds=0.1)
    queue.enqueue_run(RunId("run-a"))
    claimed = queue.claim_run(block=False)
    assert claimed is not None
    assert claimed.run_id.value == "run-a"
    queue.acknowledge_run(claimed.run_id)
    assert queue.claim_run(block=False) is None


def test_redis_run_queue_release() -> None:
    client = FakeRedis()
    queue = RedisRunQueue(client, key_prefix="test:runs")
    queue.enqueue_run(RunId("run-b"))
    claimed = queue.claim_run(block=False)
    assert claimed is not None
    queue.release_run(claimed.run_id)
    assert [r.value for r in queue.pending_run_ids()] == ["run-b"]
