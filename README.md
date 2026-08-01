# Coding Agent Evaluation Platform

Production platform for evaluating autonomous coding agents (Cursor, Claude Code, Codex, Gemini CLI, and others) against standardized evaluation cases.

> **Status:** Phase 0 — engineering foundation only. No product logic yet.

## Repository layout

```
apps/            Deployable applications (API, web)
packages/        Shared libraries and tooling config
workers/         Background / async job workers
infrastructure/  Docker scaffolding and scripts
docs/            Architecture, ADRs, API notes, diagrams
```

## Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [pnpm](https://pnpm.io/) 9+
- [Python](https://www.python.org/) 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended for Python workspace)

## Quick start

```bash
# JavaScript / TypeScript workspace
pnpm install

# Python workspace
uv sync

# Lint & format checks
pnpm lint
pnpm format:check
uv run ruff check .
uv run black --check .
```

## Documentation

| Doc                                        | Purpose                           |
| ------------------------------------------ | --------------------------------- |
| [CONTRIBUTING.md](./CONTRIBUTING.md)       | How to contribute                 |
| [SECURITY.md](./SECURITY.md)               | Vulnerability reporting           |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | Community standards               |
| [CHANGELOG.md](./CHANGELOG.md)             | Release history                   |
| [docs/](./docs/)                           | Architecture, ADRs, API, diagrams |

## License

TBD
