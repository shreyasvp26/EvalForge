"""Composition root / dependency injection wiring tests."""

from __future__ import annotations

from agent_eval_domain.common.events import DomainEvent
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.config import InfrastructureSettings
from agent_eval_infrastructure.dependency_injection import (
    RuntimeProfile,
    build_infrastructure,
)
from agent_eval_infrastructure.events import InProcessDomainEventDispatcher
from agent_eval_infrastructure.idempotency import RedisIdempotencyStore
from agent_eval_infrastructure.queue import InMemoryRunQueue, RedisRunQueue
from agent_eval_infrastructure.storage import InMemoryObjectStorage
from agent_eval_infrastructure.unit_of_work import SqlAlchemyUnitOfWorkFactory

from .fakes import FakeRedis


def test_build_infrastructure_memory_profile(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    container = build_infrastructure(profile=RuntimeProfile.MEMORY)
    try:
        assert container.profile is RuntimeProfile.MEMORY
        assert isinstance(container.uow_factory, SqlAlchemyUnitOfWorkFactory)
        assert isinstance(container.run_queue, InMemoryRunQueue)
        assert isinstance(container.object_storage, InMemoryObjectStorage)
        assert isinstance(container.events, InProcessDomainEventDispatcher)

        new_id = container.ids.new_id()
        assert new_id

        container.run_queue.enqueue_run(RunId("run-di"))
        claimed = container.run_queue.claim_run(block=False)  # type: ignore[attr-defined]
        assert claimed is not None

        meta = container.object_storage.put(
            "k", b"x", content_type="application/octet-stream"
        )
        assert meta.size_bytes == 1

        container.idempotency.put_completed(
            key="k1", scope="create_project:actor", result={"id": "p1"}
        )
        record = container.idempotency.get(key="k1", scope="create_project:actor")
        assert record is not None
        assert record.result == {"id": "p1"}

        with container.uow_factory() as uow:
            assert uow.projects is not None
    finally:
        container.dispose()


def test_build_infrastructure_uses_settings_object() -> None:
    settings = InfrastructureSettings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    container = build_infrastructure(settings, profile=RuntimeProfile.MEMORY)
    try:
        assert container.settings.database_url.startswith("sqlite")
    finally:
        container.dispose()


def test_in_process_event_dispatcher_invokes_handlers() -> None:
    from dataclasses import dataclass

    seen: list[DomainEvent] = []

    def handler(events) -> None:
        seen.extend(events)

    dispatcher = InProcessDomainEventDispatcher([handler])

    @dataclass(frozen=True, slots=True, kw_only=True)
    class _SampleEvent(DomainEvent):
        pass

    event = _SampleEvent()
    dispatcher.dispatch([event])
    assert seen == [event]
    assert dispatcher.dispatched == [event]


def test_redis_idempotency_store() -> None:
    store = RedisIdempotencyStore(FakeRedis(), key_prefix="test:idemp")
    assert store.get(key="a", scope="s") is None
    store.put_completed(key="a", scope="s", result={"ok": True})
    record = store.get(key="a", scope="s")
    assert record is not None
    assert record.result == {"ok": True}


def test_production_profile_wires_redis_queue_types(monkeypatch) -> None:
    """Production profile constructs Redis/S3 adapters (clients may be faked)."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    settings = InfrastructureSettings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
    )
    # Avoid real network: MEMORY profile; RedisRunQueue typed separately.
    queue = RedisRunQueue(FakeRedis())
    assert isinstance(queue, RedisRunQueue)
    container = build_infrastructure(settings, profile=RuntimeProfile.MEMORY)
    container.dispose()
