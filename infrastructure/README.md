# agent-eval-infrastructure

Infrastructure Layer for EvalForge.

## Why

Per Backend Architecture §4 / §5 / §11, this package provides **concrete
implementations** of Domain repository Protocols and Application ports
(Unit of Work, run queue, event dispatch, authorization, idempotency, ID
generation, object storage).

It translates between the outside world (PostgreSQL, Redis, object storage,
queues) and the Domain / Application layers.

It must remain **completely replaceable**: swapping a broker or database
engine must not require changes to Domain or Application use cases.

## Rules

| Owns                                                    | Must NOT do                                     |
| ------------------------------------------------------- | ----------------------------------------------- |
| SQLAlchemy models, sessions, migrations                 | Domain invariants or business decisions         |
| Repository adapters implementing Domain Protocols       | Authorization _policy_ (Application owns that)  |
| Unit of Work / transaction execution                    | Grading, Adapter, or Execution Engine logic     |
| Queue, object storage, ID generation adapters           | HTTP / REST concerns (API Layer)                |
| Dependency-injection composition roots for infra wiring | Validation that belongs in Domain / Application |

**Allowed dependencies:** `domain`, `application`, `shared`, and concrete
technologies (SQLAlchemy, Alembic, PostgreSQL, Redis, object storage SDKs,
queue clients).

**Forbidden:** Domain rules, business decisions, grading/adapter/execution
orchestration, authorization policy.

## Package layout

```
agent_eval_infrastructure/
  config.py                 # InfrastructureSettings (env via shared config)
  database/                 # Engine, session factory, metadata, ORM models
  mappers/                  # Explicit ORM ↔ Domain mapping (Data Mapper)
  repositories/             # Domain repository Protocol adapters
  unit_of_work/             # Application UnitOfWork implementation
  queue/                    # Redis-compatible RunQueue (+ claim/ack hooks)
  storage/                  # S3-compatible ObjectStorage for Artifacts
  ids/                      # UuidIdGenerator (Application IdGenerator port)
  events/                   # In-process DomainEventDispatcher
  idempotency/              # Redis / in-memory IdempotencyStore
  dependency_injection/     # Composition root (build_infrastructure)
  transactions/             # SAVEPOINT helper (not on Application UoW port)
  migrations/               # Alembic migration package hooks
```

## Status

Phase 5 — Infrastructure Layer feature-complete for Application ports that
Infrastructure owns: repositories, Unit of Work, run queue, object storage,
ID generation, event dispatch, idempotency, and composition root.

**Not in this package:** FastAPI, Workers, Execution Engine, Adapter/Grader
implementations, or Authorization policy.

## Composition root

```python
from agent_eval_infrastructure import (
    RuntimeProfile,
    build_infrastructure,
    load_infrastructure_settings,
)

container = build_infrastructure(profile=RuntimeProfile.MEMORY)  # tests
# container = build_infrastructure()  # production: Redis + S3-compatible
try:
    with container.uow_factory() as uow:
        ...
    container.run_queue.enqueue_run(run_id)
finally:
    container.dispose()
```

`RuntimeProfile.MEMORY` wires in-memory queue/storage/idempotency (deterministic
tests). `PRODUCTION` wires Redis + S3-compatible storage from
`InfrastructureSettings`.

Configuration flows only through `agent_eval_shared.config` /
`InfrastructureSettings` — no ad-hoc `os.environ` reads.

## Repositories

Thin persistence adapters: load ORM → map to Domain → map Domain → ORM →
persist. They never commit (Unit of Work owns transactions) and never enforce
Domain invariants.

| Protocol            | Adapter                       |
| ------------------- | ----------------------------- |
| `ProjectRepository` | `SqlAlchemyProjectRepository` |
| `SuiteRepository`   | `SqlAlchemySuiteRepository`   |
| `CaseRepository`    | `SqlAlchemyCaseRepository`    |
| `AgentRepository`   | `SqlAlchemyAgentRepository`   |
| `AdapterRepository` | `SqlAlchemyAdapterRepository` |
| `GraderRepository`  | `SqlAlchemyGraderRepository`  |
| `RunRepository`     | `SqlAlchemyRunRepository`     |

## Unit of Work

- One UoW per use-case invocation (ADR-0002)
- All repositories share one Session
- Domain events are **not** dispatched here (Application: commit → dispatch)

## Run queue

`RedisRunQueue` / `InMemoryRunQueue` implement Application `enqueue_run`.
Worker-facing `claim_run` / `acknowledge_run` / `release_run` are available on
the same adapters but contain no Worker orchestration.

## Object storage

`ObjectStorage` protocol: `put` / `get` / `delete` / `head`.
`S3CompatibleObjectStorage` uses boto3 with configurable `endpoint_url`
(MinIO, R2, AWS, … — not AWS-hardcoded). `InMemoryObjectStorage` for tests.

## Testing

Prefer `uv run pytest infrastructure/tests`. External services are mocked
(`FakeRedis`, mocked S3 client) or replaced with in-memory adapters so tests
stay deterministic.

Sibling directories in this folder (ops, not Python import graph):

- `docker/` — container and compose scaffolding
- `scripts/` — operational scripts
- `migrations/` (package root) — Alembic revision files
