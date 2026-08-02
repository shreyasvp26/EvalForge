# Contributing

Thank you for your interest in contributing to EvalForge.

## Before you start

1. Read the [Code of Conduct](./CODE_OF_CONDUCT.md).
2. Read [docs/development.md](./docs/development.md) for engineering conventions.
3. Treat [docs/architecture/](./docs/architecture/) as the source of truth — do not silently redesign boundaries.
4. Search existing issues and pull requests to avoid duplicates.
5. For significant changes, open an issue first to discuss the approach.

## Development setup

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.12+
- uv

### Install

```bash
pnpm install
uv sync
```

### Common commands

```bash
pnpm verify          # lint + format + types + tests + build
pnpm lint:fix
pnpm format
pnpm test
uv run ruff check --fix .
uv run black .
```

## Branching & commits

- Create a feature branch from `main`.
- Prefer small, focused commits with clear messages.
- Reference related issue numbers in the PR description.

## Pull requests

1. Ensure `pnpm verify` passes locally.
2. Fill out the pull request template.
3. Keep PRs focused — one concern per PR when practical.
4. Request review from the appropriate code owners.

## Reporting bugs & requesting features

Use the GitHub issue templates:

- Bug report
- Feature request

## Security

See [SECURITY.md](./SECURITY.md) for private vulnerability reporting. Do not file public issues for security concerns.
