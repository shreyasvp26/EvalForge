"""Infrastructure composition root — single assembly point for adapters.

Wires database, Unit of Work, queue, object storage, ID generation, event
dispatch, and idempotency. Does not wire Authorization (Application policy)
or FastAPI / Workers / Execution Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.run_queue import RunQueue
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from sqlalchemy import Engine

from agent_eval_infrastructure.config import (
    InfrastructureSettings,
    load_infrastructure_settings,
)
from agent_eval_infrastructure.database.engine import create_db_engine, dispose_engine
from agent_eval_infrastructure.database.session import (
    SessionFactory,
    create_session_factory,
)
from agent_eval_infrastructure.events import InProcessDomainEventDispatcher
from agent_eval_infrastructure.idempotency import (
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
)
from agent_eval_infrastructure.ids import UuidIdGenerator
from agent_eval_infrastructure.queue import (
    InMemoryRunQueue,
    RedisRunQueue,
    create_redis_client,
)
from agent_eval_infrastructure.storage import (
    InMemoryObjectStorage,
    ObjectStorage,
    S3CompatibleObjectStorage,
    create_s3_client,
)
from agent_eval_infrastructure.unit_of_work import SqlAlchemyUnitOfWorkFactory


class RuntimeProfile(StrEnum):
    """Selects concrete adapter backends at composition time."""

    PRODUCTION = "production"
    """Redis queue + S3-compatible storage + SQLAlchemy UoW."""

    MEMORY = "memory"
    """In-memory queue/storage/idempotency — for tests and local smoke runs."""


@dataclass(slots=True)
class InfrastructureContainer:
    """Assembled Infrastructure dependencies for Application / process startup."""

    settings: InfrastructureSettings
    engine: Engine
    session_factory: SessionFactory
    uow_factory: UnitOfWorkFactory
    run_queue: RunQueue
    object_storage: ObjectStorage
    ids: IdGenerator
    events: DomainEventDispatcher
    idempotency: IdempotencyStore
    profile: RuntimeProfile
    redis: object | None = None

    def dispose(self) -> None:
        """Release pooled database connections (call at process shutdown)."""
        dispose_engine(self.engine)


def build_infrastructure(
    settings: InfrastructureSettings | None = None,
    *,
    profile: RuntimeProfile | None = None,
) -> InfrastructureContainer:
    """Compose concrete Infrastructure adapters from configuration.

    ``profile`` defaults to ``MEMORY`` when ``settings.environment == \"test\"``,
    otherwise ``PRODUCTION``.
    """
    cfg = settings or load_infrastructure_settings()
    resolved = profile or (
        RuntimeProfile.MEMORY
        if cfg.environment == "test"
        else RuntimeProfile.PRODUCTION
    )

    db_settings = cfg.to_database_settings()
    engine = create_db_engine(db_settings)
    session_factory = create_session_factory(engine)
    uow_factory = SqlAlchemyUnitOfWorkFactory(session_factory)
    ids: IdGenerator = UuidIdGenerator()
    events: DomainEventDispatcher = InProcessDomainEventDispatcher()

    if resolved is RuntimeProfile.MEMORY:
        run_queue: RunQueue = InMemoryRunQueue()
        object_storage: ObjectStorage = InMemoryObjectStorage()
        idempotency: IdempotencyStore = InMemoryIdempotencyStore()
        redis_client: object | None = None
    else:
        redis_client = create_redis_client(cfg.redis_url)
        run_queue = RedisRunQueue(
            redis_client,
            key_prefix=cfg.run_queue_key_prefix,
            claim_timeout_seconds=cfg.run_queue_claim_timeout_seconds,
        )
        s3 = create_s3_client(
            endpoint_url=cfg.object_storage_endpoint_url,
            access_key=cfg.object_storage_access_key,
            secret_key=cfg.object_storage_secret_key,
            region=cfg.object_storage_region,
            force_path_style=cfg.object_storage_force_path_style,
        )
        object_storage = S3CompatibleObjectStorage(s3, bucket=cfg.object_storage_bucket)
        idempotency = RedisIdempotencyStore(redis_client)

    return InfrastructureContainer(
        settings=cfg,
        engine=engine,
        session_factory=session_factory,
        uow_factory=uow_factory,
        run_queue=run_queue,
        object_storage=object_storage,
        ids=ids,
        events=events,
        idempotency=idempotency,
        profile=resolved,
        redis=redis_client,
    )
