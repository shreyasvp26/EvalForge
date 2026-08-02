# EvalForge

Production-grade platform for evaluating autonomous coding agents (Cursor, Claude Code, Codex, Gemini CLI, and others) against standardized, reproducible evaluation cases.

> EvalForge is infrastructure, not a chatbot. Correctness and longitudinal comparability of evaluation data are the product.

## Current status

| Phase                                                | Status      |
| ---------------------------------------------------- | ----------- |
| Phase 0 — Repository foundation                      | Complete    |
| Engineering foundation (tooling, shared libs, tests) | Complete    |
| Domain layer                                         | Complete    |
| Application layer                                    | Complete    |
| Infrastructure layer                                 | In progress |
| API / workers                                        | Next        |

## Repository layout

```
apps/            Deployable applications (API, web)
packages/        TypeScript libraries (foundation, SDK, tooling config)
shared/          Python cross-cutting foundation (logging, config, errors)
domain/          Python Domain Layer (business model — source of truth)
application/     Python Application Layer (use cases, UoW, ports)
infrastructure/  Python Infrastructure adapters + Docker/ops scaffolding
workers/         Background / async job workers
docs/            Architecture, ADRs, API notes, diagrams
```

Backend module layout follows [Backend Architecture §11](./docs/architecture/backend-architecture.md). Adapters and graders packages land in later phases.

## Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quick start

```bash
pnpm install
uv sync

# Full verification (lint, format, types, tests, build)
pnpm verify
```

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

**Python**

| Package                                         | Role                                                         |
| ----------------------------------------------- | ------------------------------------------------------------ |
| `agent-eval-shared` (`shared/`)                 | Errors, settings, structlog, utilities                       |
| `agent-eval-domain` (`domain/`)                 | Aggregates, invariants, domain events, repository ports      |
| `agent-eval-application` (`application/`)       | Use cases, UoW, auth/queue/event ports, DTOs                 |
| `agent-eval-infrastructure` (`infrastructure/`) | Adapters for Domain/Application ports (scaffold in progress) |

See [docs/development.md](./docs/development.md) for conventions and dependency rules.

## Documentation

| Doc                                          | Purpose                               |
| -------------------------------------------- | ------------------------------------- |
| [docs/development.md](./docs/development.md) | Engineering conventions               |
| [docs/architecture/](./docs/architecture/)   | System architecture (source of truth) |
| [CONTRIBUTING.md](./CONTRIBUTING.md)         | Contribution workflow                 |
| [SECURITY.md](./SECURITY.md)                 | Vulnerability reporting               |

## License

TBD
