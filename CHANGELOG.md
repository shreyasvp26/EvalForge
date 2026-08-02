# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Phase 0 repository foundation (monorepo, tooling, CI scaffolding)
- Engineering foundation: shared TS packages (`errors`, `env`, `logger`, `utils`), Python `shared/`, Vitest/pytest, Husky, root verify scripts
- Domain Layer: pure Python aggregates, versioning, Run lifecycle, NDM, repository ports, unit tests
- Application Layer: use cases, Unit of Work / event / queue / auth ports, DTOs, Domain error translation, orchestration unit tests
- Infrastructure Layer: package scaffold (`agent-eval-infrastructure`) colocated with existing Docker/ops assets
- Infrastructure SQLAlchemy foundation: Engine, Session factory, declarative Base, naming conventions, Schema Design ORM models, repository base (no repository methods yet)
- Infrastructure SQLAlchemy repository adapters for every Domain repository Protocol, explicit ORM ↔ Domain mappers, SQLite repository unit tests (including Run optimistic locking)
- Infrastructure transactional Unit of Work (`SqlAlchemyUnitOfWork` / factory): shared-session repositories, commit/rollback, optimistic concurrency propagation; no domain-event dispatch
- Infrastructure service adapters and composition root: Redis-compatible run queue, S3-compatible object storage, UUID ID generator, in-process event dispatcher, idempotency stores, `InfrastructureSettings`, `build_infrastructure`
- Execution Worker runtime scaffold: `worker`, `execution_engine`, `scheduler`, `lifecycle`, `cancellation`, `checkpoints`, `event_pipeline` packages (structure only)
- Execution Worker Run lifecycle orchestration: explicit phase machine, validated transitions, failure/cancel/timeout paths, subsystem ports, Domain `RunStatus` projection mapping, lifecycle unit tests
- Execution Worker runtime orchestration: `WorkerRuntime` claim/ack/release loop, retry policy, cooperative cancellation, execution timeouts, checkpoint create/restore, `ExecutionEngine` host, worker unit tests (mocked queue + lifecycle)
- Event persistence pipeline: Application `RecordExecutionEvent` / idempotent `RecordArtifact`, Domain append-only idempotent replay, worker `EventPersistencePipeline` with ordered batching, projection hooks, and `PersistenceFailure` reporting
