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

Copy `.env.example` to `.env` at the **repository root**. Settings loaders resolve
that file from the monorepo root (not the process CWD), so starting the API from
`apps/api` still picks up the same configuration.

Local interactive development must use:

| Setting          | Value                                                      |
| ---------------- | ---------------------------------------------------------- |
| `ENVIRONMENT`    | `development` (never `test` for the running API/web stack) |
| `DATABASE_URL`   | PostgreSQL (`postgresql+psycopg://…`)                      |
| `REDIS_URL`      | Redis (`redis://localhost:6379/0`)                         |
| `JWT_SECRET_KEY` | ≥ 32 characters; never `change-me-in-production`           |

`ENVIRONMENT=test` is reserved for pytest. Pairing it with a file-backed SQLite
`DATABASE_URL` (especially under `/tmp/evalforge*.db`) boots MEMORY identity while
domain APIs hit an empty SQLite database — configuration validation rejects that
footgun for development/production and for `/tmp/evalforge*` URLs.

Baseline keys today:

| Variable                   | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| `NODE_ENV` / `ENVIRONMENT` | `development` \| `test` \| `production`          |
| `LOG_LEVEL`                | Logging verbosity                                |
| `DATABASE_URL`             | SQLAlchemy PostgreSQL URL                        |
| `REDIS_URL`                | Redis for run queue / idempotency                |
| `JWT_SECRET_KEY`           | HS256 signing secret (≥ 32 chars)                |
| `CORS_ORIGINS`             | Browser origins allowed to call the API          |
| `OBJECT_STORAGE_*`         | S3-compatible Artifact store (endpoint optional) |
| `ANTHROPIC_API_KEY`        | Anthropic judge provider (optional)              |
| `OPENAI_API_KEY`           | OpenAI judge provider (optional)                 |
| `GEMINI_API_KEY`           | Gemini judge provider (optional)                 |

Service-specific schemas should **extend** the baseline, not replace it.
Load Python settings via `agent_eval_shared.config.load_settings` /
`agent_eval_infrastructure.load_infrastructure_settings` — never ad-hoc
`os.environ` outside those loaders.

Migrations (from repository root):

```bash
uv run alembic -c infrastructure/alembic.ini upgrade head
```

## Testing

| Layer           | Tool   | Location                                                                                                                                                                    |
| --------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TypeScript unit | Vitest | `*.test.ts` next to source or under `tests/`                                                                                                                                |
| Python unit     | pytest | `shared/tests/`, `domain/tests/`, `application/tests/`, `infrastructure/tests/`, `workers/tests/`, `sandbox/tests/`, `adapters/tests/`, `graders/tests/`, `apps/api/tests/` |

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
- **Read surface:** list/get use cases for Projects, Suites, Cases, Agents,
  Adapters, Graders, and Runs, plus Run nested reads (`GetRunEvents`,
  `GetRunArtifacts`, `GetRunScores`). Returns frozen DTOs only. Future REST
  routers must call these use cases — never Domain repositories directly.
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
- Subpackages: `worker`, `execution_engine`, `integration`, `scheduler`,
  `lifecycle`, `cancellation`, `checkpoints`, `event_pipeline`, `mocks`.
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
  grading only after final event persistence.
- **Production pipeline (Phase 11):** `build_production_harness` replaces
  mocks with `ManagedSandboxAdapter` (Docker via SandboxPort),
  `SdkAdapterBridge` (Claude Code via Adapter SDK), `GraderSdkScheduler`
  (objective + rubric via `run_graders_isolated`), and Application
  `StartRun` / `StartGrading` / `RecordScore` / `CompleteRun`. Engine stays
  Docker-unaware; Workers stay Claude-unaware outside composition.
  Integration tests mock only `MockJudgeProvider`. See `workers/README.md`.
- **Process wiring (Phase 1 / Phase 2):** `evalforge-worker`
  (`agent_eval_workers.main`) uses `build_production_worker` so Redis
  claims drive `LifecycleOrchestrator` against real Application UoW /
  pin-resolved objective graders / object storage artifacts.
  - **Compose / production-like:** `WORKER_SANDBOX_ENGINE=docker` (Docker
    socket mounted), `WORKER_ADAPTER_MODE=deterministic` by default,
    `WORKER_SANDBOX_IMAGE=evalforge/sandbox:local`. Core stack via
    `docker compose ... up`; add `--profile full` for the web UI image.
  - **Local without Docker:** `WORKER_SANDBOX_ENGINE=auto|fake` falls back
    to `FakeDockerEngine`; deterministic Claude stream remains available.
  - **Live Claude CLI:** `WORKER_ADAPTER_MODE=claude` +
    `ANTHROPIC_API_KEY` (allow-listed into the sandbox) + CLI in the
    sandbox image + `WORKER_SANDBOX_NETWORK=bridge`.
  - Optional `WORKER_SANDBOX_VERIFY=1` runs a post-provision `true` exec.
  - Cancellation: API publishes Redis cancel signals
    (`RUN_CANCEL_KEY_PREFIX`); workers observe cooperatively.
  - Start: `uv run evalforge-worker` or
    `docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up --build`.
  - Cover with `uv run pytest workers/tests/test_process_worker.py` and
    optional live Docker: sandbox `-m integration`, or
    `EVALFORGE_LIVE_WORKER_DOCKER=1` for the worker Docker e2e.
  - See `infrastructure/docker/README.md`.
- **Must not** contain Adapter translation, Grader scoring, or Domain
  invariants; must not bypass Application for business writes.
- Prefer `uv run pytest workers/tests` for worker-only feedback.

## Sandbox Runtime

Python package: `sandbox/` → `agent_eval_sandbox`.

- First production execution component: isolated Docker execution only.
- Interfaces: `create` / `start` / `execute` / `copy_out` / `stop` / `destroy`.
- Enforces CPU, memory, disk (best-effort), timeout, working directory, and
  readonly mounts; default network is deny-all (`NetworkMode.NONE`).
- `SandboxManager.session` and `docker.cleanup.ensure_destroyed` always tear
  down containers after timeout, failure, or worker interruption.
- **Must not** import Domain, Application, Workers, Adapters, or Graders.
- Depends on `agent-eval-shared` + `docker` only.
- Prefer `uv run pytest sandbox/tests` (mocked Docker). Optional live Docker:
  `uv run pytest sandbox/tests -m integration`.
- See `sandbox/README.md`.

## Adapter Layer

Python package: `adapters/` → `agent_eval_adapters`.

- **SDK:** `Adapter` contract, immutable `ExecutionContext`, `LifecycleDriver`
  (`initialize` → `prepare` → `start` → `stream` → `finish` → `cleanup`),
  `EventEmitter` (ordered, exactly-once via `EventSink` ports — never
  repositories), `DefaultTranslator` (NativeObservation → NDM).
- **Claude Code Adapter:** observes `--output-format stream-json`, maps tool
  calls / file edits / shell / stdout / completion / errors; supports
  cancellation and timeout between stream lines.
- **Additional production adapters (Phase 13):** Cursor (`agent`), Codex CLI
  (`codex exec --json`), Gemini CLI (`gemini --output-format stream-json`),
  and Aider (`aider --message`) — same Adapter SDK lifecycle and NDM
  translation contract; injectable `stream_source` for mocked tests.
- Depends on `domain` (NDM), `shared`, and `sandbox` only.
- **Must not** import Application, Infrastructure, Workers, Execution Engine,
  Graders, or FastAPI.
- Prefer `uv run pytest adapters/tests` (mocked Sandbox / streams only).
- See `adapters/README.md`.

## Grader Layer

Python package: `graders/` → `agent_eval_graders`.

- **SDK:** `Grader` contract, immutable `GradingContext`, `LifecycleDriver`
  (`initialize` → `read_run` → `grade` → `produce_scores` → `cleanup`),
  `RunReader` / `ScoreSink` ports, `run_grader` / `run_graders_isolated`.
- **Objective graders:** BuildSuccess, ExitCode, TestPass, Lint,
  ExpectedFile, DiffValidation, JSONOutput — deterministic reads of
  recorded Execution Events / Artifacts only.
- **Rubric graders:** `RubricGrader` + injectable `JudgeProvider` /
  `MockJudgeProvider`; prompt builder (Run record + pinned rubric only);
  strict response parser; rubric wording immutable per Grader Version.
  Production providers: Anthropic / OpenAI / Gemini under
  `agent_eval_graders.providers` (same `JudgeProvider` port; mocked HTTP
  tests only — no live LLM calls in CI).
- Produces immutable Domain `Score` / `ScoreValue` (pass/fail, numeric,
  reason, metadata, grader version, timestamps).
- Sibling grader failures never affect each other (`run_graders_isolated`).
- Depends on `domain` + `shared` (+ `httpx` for judge providers) only.
  Rubric family uses the shared Grader SDK; does not modify objective
  graders or the Grader lifecycle.
- **Must not** import Application, Infrastructure, Workers, Execution
  Engine, Sandbox, Adapters, or FastAPI.
- Prefer `uv run pytest graders/tests`.
- See `graders/README.md` and
  `docs/architecture/grader-architecture.md`.

## API Layer / Control Plane

Python package: `apps/api/` → `agent_eval_api`.

- **Phase 6A:** FastAPI factory, lifespan, composition root, Bearer auth
  boundary, correlation/timing/request-logging middleware, centralized error
  mapping, OpenAPI, health/readiness, `/v1` root.
- **Phase 6B:** versioned business routers under `routers/v1/` for Projects,
  Suites, Cases, Prompt/Case Versions, Agents, Adapters, Graders, Runs, and
  nested Run Events / Artifacts / Scores. Routers map Pydantic schemas ↔
  Application Commands/Queries/DTOs only.
- Composition root: `build_api_container()` / `build_application_services()`.
- **Must not** import Domain entities into routers, open SQLAlchemy sessions,
  touch Redis/S3, or contain business rules.
- Prefer `uv run pytest apps/api/tests` for API-only feedback.

## What does not belong in foundation packages

- HTTP handlers, SQL/ORM, queue consumers
- Adapter or Grader _implementations_ (interfaces/contracts may live in Domain)
- UI components (those live in `@agent-eval/ui` / `apps/web` — see below)

## Frontend (Phases 15A–15B)

| Package                          | Role                                                              |
| -------------------------------- | ----------------------------------------------------------------- |
| `@agent-eval/ui` (`packages/ui`) | Tokens, primitives, DataGrid, Storybook                           |
| `@agent-eval/web` (`apps/web`)   | App Router shell, layouts, patterns, navigation, `/design-system` |

**Hybrid ownership:** domain UI and product chrome stay in `apps/web`. Never put `RunCard` / `ProjectCard` / `ScorePanel` in `packages/ui`.

Read first:

- [docs/design/design-principles.md](./design/design-principles.md)
- [docs/design/developer-guidelines.md](./design/developer-guidelines.md)
- [docs/design/layouts.md](./design/layouts.md)
- [docs/design/product-patterns.md](./design/product-patterns.md)
- [docs/design/navigation.md](./design/navigation.md)
- [docs/design/data-grid.md](./design/data-grid.md)
- [docs/adr/ADR-0003-frontend-design-system.md](./adr/ADR-0003-frontend-design-system.md)

```bash
pnpm --filter @agent-eval/web dev          # http://localhost:3000
pnpm --filter @agent-eval/ui storybook     # engineering playground
pnpm verify                                # required before commit
```

Web structure:

```
apps/web/src/
  app/(shell)/          # routes inside AppShell
  components/shell/     # sidebar, ⌘K, breadcrumbs, hotkeys
  components/layouts/   # PageLayout, PageHeader, …
  components/patterns/  # skeletons, ConfirmationDialog, …
```
