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
orchestration.

## Package layout

```
agent_eval_infrastructure/
  database/                 # Engine, session factory, metadata, ORM models
  mappers/                  # Explicit ORM ↔ Domain mapping (Data Mapper)
  repositories/             # Domain repository Protocol adapters
  unit_of_work/             # Application UnitOfWork implementation
  queue/                    # Run queue / messaging adapters
  storage/                  # Object storage adapters
  ids/                      # ID generator implementations
  transactions/             # Transaction helpers shared by UoW / repos
  dependency_injection/     # Composition / wiring helpers
  migrations/               # Alembic migration package hooks (versions live below)
```

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

**Mapping rules:** Version _content_ is insert-once; version _lifecycle status_
may be updated in place to match Domain Model §7. Run children (events,
artifacts, scores) are append-only. Run `lock_version` is SQLAlchemy-managed
optimistic concurrency (not a Domain field). Sandbox is Domain-only and is
reconstructed as `None`.

Sibling directories in this folder (ops, not Python import graph):

- `docker/` — container and compose scaffolding
- `scripts/` — operational scripts
- `migrations/` (package root) — Alembic revision files (Phase 2+)

## Status

Phase 4 — SQLAlchemy Unit of Work implements the Application `UnitOfWork`
port (session + transaction lifecycle, repository factories, commit/rollback).
Redis, queue, object storage, DI, and Alembic revisions land in Phase 5+.

## Unit of Work

```
unit_of_work/
  sqlalchemy.py   # SqlAlchemyUnitOfWork + SqlAlchemyUnitOfWorkFactory
```

- One UoW per use-case invocation (ADR-0002); nested `__enter__` is rejected
- All repositories from one UoW share the exact same `Session`
- Repositories never commit/rollback — UoW owns that
- Domain events are **not** dispatched here (Application: commit → dispatch)
- Optimistic concurrency: `StaleDataError` propagates from flush/commit
- Nested SAVEPOINTs are **not** on the Application port; optional helper
  `transactions.begin_nested` exists for rare Infrastructure call sites

## Database package

```
database/
  config.py       # DatabaseSettings (DATABASE_URL, pool)
  naming.py       # Constraint/index naming conventions
  base.py         # Declarative Base + MetaData
  mixins.py       # UUID PK, timestamps, optimistic lock
  engine.py       # create_db_engine / dispose_engine
  session.py      # sessionmaker + session_scope
  models/         # Persistence models (Schema Design logical tables)
```

**Rules:** ORM models never leave Infrastructure. Domain stays
persistence-agnostic (Data Mapper). Sync SQLAlchemy only — architecture does
not require async ORM for the Control Plane.

## Testing

Repository unit tests use in-memory SQLite (`sqlite+pysqlite:///:memory:`).
Prefer `uv run pytest infrastructure/tests`. PostgreSQL-specific behavior
and testcontainers arrive with later phases.
