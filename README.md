# EvalForge

Production-grade platform for evaluating autonomous coding agents (Cursor, Claude Code, Codex, Gemini CLI, and others) against standardized, reproducible evaluation cases.

> EvalForge is infrastructure, not a chatbot. Correctness and longitudinal comparability of evaluation data are the product.

## Current status

| Phase                                                   | Status      |
| ------------------------------------------------------- | ----------- |
| Phase 0 — Repository foundation                         | Complete    |
| Engineering foundation (tooling, shared libs, tests)    | Complete    |
| Domain layer                                            | Complete    |
| Application layer                                       | Complete    |
| Infrastructure layer                                    | Complete    |
| Execution workers / engine                              | Complete    |
| FastAPI Control Plane (Phase 6)                         | Complete    |
| Sandbox Runtime (Phase 7)                               | Complete    |
| Adapter SDK + Claude Code (Phase 8)                     | Complete    |
| Objective Graders (Phase 9)                             | Complete    |
| Rubric Graders (Phase 10)                               | Complete    |
| Production Pipeline Integration (Phase 11)              | Complete    |
| Production Judge Providers (Phase 12)                   | Complete    |
| Multi-Agent Adapter Expansion (Phase 13)                | Complete    |
| Production Hardening (Phase 14)                         | Complete    |
| Phase 15A — Frontend design system foundation           | Complete    |
| Phase 15B — Product UX foundation                       | Complete    |
| Phase 16 — Product implementation (Projects → Overview) | In progress |
| Additional adapters / remaining product CRUD UI         | Later       |

## Repository layout

```
apps/            Deployable applications (API, web)
packages/        TypeScript libraries (foundation, SDK, tooling config)
shared/          Python cross-cutting foundation (logging, config, errors)
domain/          Python Domain Layer (business model — source of truth)
application/     Python Application Layer (use cases, UoW, ports)
infrastructure/  Python Infrastructure adapters + Docker/ops scaffolding
workers/         Background / async job workers (Execution Engine host)
sandbox/         Sandbox Runtime — isolated Docker execution only
adapters/        Adapter SDK + vendor adapters (Claude Code first)
graders/         Grader SDK + objective graders (measurement only)
docs/            Architecture, ADRs, API notes, diagrams
```

Backend module layout follows [Backend Architecture §11](./docs/architecture/backend-architecture.md).

## Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quick start

```bash
pnpm install
uv sync --all-packages

# Full verification (lint, format, types, tests, build)
pnpm verify
```

### Docker (production-shaped local stack)

```bash
cp .env.example .env   # set JWT_SECRET_KEY
docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up --build
```

See [infrastructure/docker/README.md](./infrastructure/docker/README.md) for services,
healthchecks, volumes, and startup order.

## Common scripts

| Script                              | Purpose                             |
| ----------------------------------- | ----------------------------------- |
| `pnpm build`                        | Build all TypeScript packages       |
| `pnpm lint` / `pnpm lint:fix`       | ESLint                              |
| `pnpm format` / `pnpm format:check` | Prettier                            |
| `pnpm typecheck`                    | TypeScript project-references check |
| `pnpm test`                         | Vitest (TS) + pytest (Python)       |
| `pnpm clean`                        | Remove build outputs                |
| `pnpm verify`                       | CI-equivalent local gate            |

Python-only:

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

## Foundation packages

**TypeScript**

| Package              | Role                                                  |
| -------------------- | ----------------------------------------------------- |
| `@agent-eval/config` | Shared ESLint / Prettier / TS / Vitest tooling config |
| `@agent-eval/errors` | Typed error hierarchy                                 |
| `@agent-eval/env`    | Zod-validated environment loading                     |
| `@agent-eval/logger` | Structured logging + correlation context              |
| `@agent-eval/utils`  | Small cross-cutting helpers                           |
| `@agent-eval/shared` | Barrel re-exports of the above                        |
| `@agent-eval/ui`     | Design tokens, primitives, DataGrid, Storybook        |
| `@agent-eval/web`    | Next.js app (shell, layouts, patterns) — see below    |

**Python**

| Package                                         | Role                                                    |
| ----------------------------------------------- | ------------------------------------------------------- |
| `agent-eval-shared` (`shared/`)                 | Errors, settings, structlog, utilities                  |
| `agent-eval-domain` (`domain/`)                 | Aggregates, invariants, domain events, repository ports |
| `agent-eval-application` (`application/`)       | Use cases, UoW, auth/queue/event ports, DTOs            |
| `agent-eval-infrastructure` (`infrastructure/`) | Adapters for Domain/Application ports + composition     |
| `agent-eval-workers` (`workers/`)               | Execution Engine host, lifecycle, event pipeline        |
| `agent-eval-sandbox` (`sandbox/`)               | Isolated Docker sandbox runtime (no orchestration)      |
| `agent-eval-adapters` (`adapters/`)             | Adapter SDK + Claude Code (NDM translation only)        |
| `agent-eval-graders` (`graders/`)               | Grader SDK + objective + rubric graders (Domain Scores) |
| `agent-eval-api` (`apps/api`)                   | FastAPI Control Plane over Application use cases        |

See [docs/development.md](./docs/development.md) for conventions and dependency rules.

## Frontend architecture

EvalForge’s UI is a **renderer** over the API (backend owns the product). Phase 15A/15B established:

1. **`@agent-eval/ui`** — design tokens, semantic typography/icons, primitives, DataGrid
2. **`apps/web`** — AppShell (sidebar + top bar + ⌘K), product layouts, UX patterns, `/design-system`

Hybrid ownership is locked in [ADR-0003](./docs/adr/ADR-0003-frontend-design-system.md). Domain components never live in `packages/ui`.

```bash
pnpm --filter @agent-eval/web dev
pnpm --filter @agent-eval/ui storybook
```

Docs: [docs/design/](./docs/design/) (principles, layouts, patterns, navigation, DataGrid, contributor guidelines).

## Documentation

| Doc                                          | Purpose                               |
| -------------------------------------------- | ------------------------------------- |
| [docs/development.md](./docs/development.md) | Engineering conventions               |
| [docs/design/](./docs/design/)               | Frontend design + UX foundation       |
| [docs/architecture/](./docs/architecture/)   | System architecture (source of truth) |
| [CONTRIBUTING.md](./CONTRIBUTING.md)         | Contribution workflow                 |
| [SECURITY.md](./SECURITY.md)                 | Vulnerability reporting               |

## License

TBD
