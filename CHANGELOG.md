# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Phase 16 Milestone 8 — Live execution experience: polling while queued/running/grading, execution chrome, grouped expandable timeline, tabbed artifact viewer, expandable score viewer, SSE-ready `useRunPolling` seam
- Phase 16 Milestone 7 — Runs & execution management: project-filtered list, multi-step create wizard with pinned versions + Idempotency-Key, flagship detail (timeline/artifacts/scores), cancel confirmation, command-palette actions
- Phase 16 Milestone 6 — Graders management: platform-scoped list/create/detail, family badges, draft/publish versions with specification preview, command-palette actions
- Phase 16 Milestone 5 — Agents & Adapter management: platform-scoped list/create/detail, agent draft/publish, connect adapter, adapter detail with draft/publish, command-palette actions
- Phase 16 Milestone 4 — Cases & Prompt Versions: project-scoped list/create/detail, prompt draft/publish, case draft/publish, deprecate, Cases index project picker, command-palette actions
- Phase 16 Milestone 3 — Suites product experience: project-scoped list/create/detail, draft/publish/retire version management, read-only composition viewer, Suites index project picker, command-palette actions
- Phase 16 Milestone 2 — Projects product experience: list (`/projects` DataGrid with search/sort), create dialog, detail overview, settings (rename / settings map / deprecate), navigation + command palette actions, React Query over Control Plane REST
- Phase 16 Milestone 1 — Authentication experience: login/logout/me against JWT Control Plane, protected shell routes, session persistence, user menu
- Phase 15B product UX foundation: product layouts (`PageLayout`, `PageHeader`, `Section`, `Toolbar`, `FilterBar`, `DetailLayout`, `SplitView`), domain-agnostic `DataGrid`, UX patterns (skeletons, empty/error/confirm), navigation polish (collapsible sidebar, ⌘K, shortcuts, breadcrumbs, mobile drawer), design docs + Storybook Docs MDX
- Phase 15A frontend design system foundation: `docs/design` principles + ADR-0003, `@agent-eval/ui` tokens/primitives/Storybook, Next.js `apps/web` shell (sidebar + top bar + lazy ⌘K command palette + opt-in inspector), `/design-system` gallery, light/dark theme
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
- Execution Engine end-to-end orchestration: mocked Sandbox/Adapter/Grader wiring, continuous event streaming into the Event Pipeline, grading-after-execution scheduler, `build_orchestration_harness`, and comprehensive orchestration tests
- FastAPI Control Plane (`apps/api`): composition root, Bearer auth boundary, middleware, error mapping, OpenAPI, health/system endpoints, and v1 routers for Projects, Suites, Cases, Prompts, Agents, Adapters, Graders, and Runs (Application use cases only; mocked API tests)
- FastAPI Control Plane foundation (Phase 6A): application factory, lifespan, DI/composition root, correlation/timing/request-logging middleware, centralized error mapping, auth boundary, OpenAPI, `/v1` root, health/readiness — business resource routes deferred to Phase 6B
- Application read surface: `ListProjects`, `ListAgents`, `ListAdapters`, `GetAdapter`, `ListGraders`, `GetRunEvents`, `GetRunArtifacts`, `GetRunScores` (frozen DTOs; Domain `list_all` on Project/Agent/Adapter/Grader repositories)
- FastAPI Control Plane REST API (Phase 6B): versioned `/v1` routers for Projects, Suites, Cases, Prompts, Agents, Adapters, Graders, Runs (incl. nested events/artifacts/scores); Pydantic schemas; Idempotency-Key on creates; TestClient integration tests
- Sandbox Runtime (Phase 7): `agent-eval-sandbox` package — Docker-backed isolated execution (`create`/`start`/`execute`/`copy_out`/`stop`/`destroy`), resource limits, default-deny networking, mandatory cleanup, FakeDockerEngine unit tests + optional live Docker integration tests
- Adapter SDK + Claude Code Adapter (Phase 8): `agent-eval-adapters` package — SDK lifecycle/context/emitter/translator; Claude Code stream-json adapter; mocked-Sandbox integration tests (no Workers/Graders)
- Objective Grader Engine (Phase 9): `agent-eval-graders` package — Grader SDK lifecycle (`initialize`→`read_run`→`grade`→`produce_scores`→`cleanup`), RunReader isolation, seven deterministic objective graders, Domain Score production, sibling-failure isolation (`run_graders_isolated`)
- Rubric Grader Engine (Phase 10): rubric family over shared Grader SDK — immutable `RubricSpecification`, prompt builder (Run record only), injectable `JudgeProvider`/`MockJudgeProvider`, strict response parser, failure classification (timeout / unavailable / schema), mock-only tests (no external LLMs)
- Production Pipeline Integration (Phase 11): Worker `integration/` composition replaces MockSandbox / MockAdapter / MockGraders with Docker Sandbox, Claude Code Adapter SDK, objective + rubric Graders, and Application score/lifecycle use cases; end-to-end production tests (mock JudgeProvider only)
- Production Judge Providers (Phase 12): Anthropic / OpenAI / Gemini plugins implementing `JudgeProvider` with env config, exponential backoff, mapped platform failures, determinism passthrough; mocked-HTTP tests only (no live LLM calls)
- Multi-Agent Adapter Expansion (Phase 13): Cursor, Codex CLI, Gemini CLI, and Aider production adapters over the existing Adapter SDK — NDJSON stream parsing, NDM translation, cancellation/timeout between lines; mocked stream-source tests only

### Changed

- Phase 15B final polish: command palette focus trap (Radix Dialog), collapsed sidebar accessible names, skip link, mobile search affordance, lazy shortcuts dialog, Coming Soon route alignment, `NotFoundState` on 404, shell `loading.tsx`, tokenized radii (`--ef-radius-tight`), motion helpers wired to shared duration tokens, responsive SplitView / InspectorLayout / DataGridPagination
