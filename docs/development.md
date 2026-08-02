# Development guide

This document explains how the EvalForge engineering foundation is meant to be used. Architecture documents under `docs/architecture/` remain the source of truth for product structure.

## Principles

1. **Strict TypeScript** — `any` is forbidden; shared tsconfig enforces `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, and `verbatimModuleSyntax`.
2. **No duplicated config** — extend `@agent-eval/config` instead of copying compiler/lint options.
3. **Fail fast on configuration** — validate env/settings at process startup via `@agent-eval/env` / `agent_eval_shared.config`.
4. **Structured logs + correlation** — attach correlation/run/worker IDs at API and Worker entry points; Domain does not log.
5. **Typed errors** — use shared error classes; never conflate infrastructure failure with an agent failing a case.

## Dependency rules (backend)

From Backend Architecture §5 / §11:

- `domain` → `shared` only (and nothing else)
- `application` → `domain` + `shared` only (never Infrastructure, FastAPI, SQLAlchemy, Redis, …)
- `infrastructure` → `domain` + `application` + `shared` + concrete tech (SQLAlchemy, Redis, …)
- `shared` → nothing else in the backend tree
- Domain **must not** import config or logging modules
- Application **must not** contain domain invariants or transport/persistence details
- Adapters / Graders → Domain + shared only

TypeScript foundation packages mirror the same idea for the Presentation / SDK plane:

```
@agent-eval/utils
@agent-eval/errors
@agent-eval/env      → errors
@agent-eval/logger   → env (types), utils
@agent-eval/shared   → barrel of the above
```

## Environment variables

Copy `.env.example` to `.env`. Do not read `process.env` / `os.environ` outside the configuration packages except inside those packages' loaders.

Baseline keys today:

| Variable                   | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| `NODE_ENV` / `ENVIRONMENT` | `development` \| `test` \| `production`          |
| `LOG_LEVEL`                | Logging verbosity                                |
| `DATABASE_URL`             | SQLAlchemy PostgreSQL URL                        |
| `REDIS_URL`                | Redis for run queue / idempotency                |
| `OBJECT_STORAGE_*`         | S3-compatible Artifact store (endpoint optional) |

Service-specific schemas should **extend** the baseline, not replace it.
Load Python settings via `agent_eval_shared.config.load_settings` /
`agent_eval_infrastructure.load_infrastructure_settings` — never ad-hoc
`os.environ` outside those loaders.

## Testing

| Layer           | Tool   | Location                                                                                                             |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------- |
| TypeScript unit | Vitest | `*.test.ts` next to source or under `tests/`                                                                         |
| Python unit     | pytest | `shared/tests/`, `domain/tests/`, `application/tests/`, `infrastructure/tests/`, `workers/tests/`, `apps/api/tests/` |

Run everything with `pnpm test`. Coverage: `pnpm test:coverage`.

Do not add low-value tests that only assert implementation details. Prefer tests that lock invariants of foundation behavior (fail-fast config, error serialization, correlation context).

## Git hooks

Husky runs `lint-staged` on pre-commit (ESLint/Prettier for TS/JS; Ruff/Black for Python). Hooks are installed via the root `prepare` script on `pnpm install`.

## Builds

Library packages emit declarations and JS to `dist/` via `tsc -b` (project references). Workspace runtime resolution currently points at `src/` for fast local iteration; `pnpm build` still verifies emit is clean and deterministic.

## Domain Layer

Python package: `domain/` → `agent_eval_domain`.

- Organized by bounded contexts (`evaluation_management`, `execution`,
  `agent_integration`, `grading`, `versioning`).
- Depends only on `agent_eval_shared` (error bases / tiny helpers).
- **Must not** import config, logging, HTTP, ORM, queues, adapters, or graders.
- Repository interfaces live in `agent_eval_domain.repositories`; Infrastructure
  implements them in a later phase.
- Prefer `uv run pytest domain/tests` for domain-only feedback.

## Application Layer

Python package: `application/` → `agent_eval_application`.

- Owns use-case orchestration, Project-scoped authorization, Unit of Work
  boundaries, idempotency of use-case invocation, and Domain error translation.
- Depends on `agent_eval_domain` + `agent_eval_shared` only.
- Defines Application ports (Unit of Work, event dispatcher, run queue,
  authorization, idempotency) that Infrastructure implements later.
- **Must not** import FastAPI, SQLAlchemy, Redis, Celery, HTTP, or JSON
  transport concerns.
- Business rules stay in Domain; Application coordinates aggregates and commits.
- Prefer `uv run pytest application/tests` for application-only feedback
  (ports are mocked — never a real database or broker).

## Infrastructure Layer

Python package: `infrastructure/` → `agent_eval_infrastructure`
(colocated with existing `docker/` and `scripts/` ops assets).

- Implements Domain repository Protocols and Application ports (UoW, run
  queue, event dispatch, idempotency, ID generation) plus object storage.
- Composition root: `build_infrastructure()` / `InfrastructureContainer`.
- Depends on `domain`, `application`, `shared`, and concrete technologies.
- **Must not** contain Domain rules, authorization policy, grading, adapters,
  or execution orchestration.
- Prefer `uv run pytest infrastructure/tests` for infrastructure-only feedback.

## Workers / Execution Runtime

Python package: `workers/` → `agent_eval_workers`.

- Thin chassis hosting the Execution Engine (Backend Architecture §4 / §7).
- Subpackages: `worker`, `execution_engine`, `scheduler`, `lifecycle`,
  `cancellation`, `checkpoints`, `event_pipeline`, `mocks`.
- **Lifecycle (Phase 2):** `RunLifecycle` + `LifecycleOrchestrator` own
  orchestration sequencing and illegal-transition rejection. Ports for
  Sandbox / Adapter / events / grading / status are interfaces only.
  Domain `RunStatus` remains the persisted projection.
- **Worker runtime (Phase 3):** `WorkerRuntime` owns queue leases, retries,
  heartbeats, and shutdown; `ExecutionEngine` owns lifecycle sequencing with
  cancel/timeout propagation; checkpoints via `CheckpointStore` ports only.
- **Event pipeline (Phase 4):** `EventPersistencePipeline` writes Execution
  Events and Artifacts only through Application use cases
  (`RecordExecutionEvent`, `RecordArtifact`); ordered, idempotent, with
  projection hooks for future live consumers.
- **End-to-end orchestration (Phase 5):** `build_orchestration_harness`
  wires Worker + Engine + Lifecycle + Event Pipeline + mock Sandbox /
  Adapter / Graders. Continuous event streaming during Adapter `run`;
  grading only after final event persistence. See `workers/README.md`.
- **Must not** contain Adapter translation, Grader scoring, or Domain
  invariants; must not bypass Application for business writes.
- Prefer `uv run pytest workers/tests` for worker-only feedback.

## API Layer / Control Plane

Python package: `apps/api/` → `agent_eval_api`.

- FastAPI Control Plane: authenticate, validate request shape, invoke
  Application use cases, serialize DTOs, map errors to HTTP.
- Composition root: `build_api_container()` wires Application ← Infrastructure
  ← Configuration. Routers consume `ApplicationServices` only.
- **Must not** import Domain entities into routers, open SQLAlchemy sessions,
  touch Redis/S3, or contain business rules.
- Auth boundary: Bearer → `Actor`; authorization policy remains Application
  (`AllowAllAuthorization` stub until real policies land).
- Prefer `uv run pytest apps/api/tests` for API-only feedback (Application
  services are mocked — never a live database).

## What does not belong in foundation packages

- HTTP handlers, SQL/ORM, queue consumers
- Adapter or Grader _implementations_ (interfaces/contracts may live in Domain)
- UI components
