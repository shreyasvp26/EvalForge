# Contributing

Thank you for your interest in contributing to the Coding Agent Evaluation Platform.

## Before you start

1. Read the [Code of Conduct](./CODE_OF_CONDUCT.md).
2. Search existing issues and pull requests to avoid duplicates.
3. For significant changes, open an issue first to discuss the approach.

## Development setup

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.12+
- uv (recommended)

### Install

```bash
pnpm install
uv sync
```

### Common commands

```bash
# TypeScript / JS
pnpm lint
pnpm format
pnpm format:check

# Python
uv run ruff check .
uv run ruff check --fix .
uv run black .
uv run black --check .
```

## Branching & commits

- Create a feature branch from `main`.
- Prefer small, focused commits with clear messages.
- Reference related issue numbers in the PR description.

## Pull requests

1. Ensure lint and format checks pass locally.
2. Fill out the pull request template.
3. Keep PRs focused — one concern per PR when practical.
4. Request review from the appropriate code owners.

## Reporting bugs & requesting features

Use the GitHub issue templates:

- Bug report
- Feature request

## Security

See [SECURITY.md](./SECURITY.md) for private vulnerability reporting. Do not file public issues for security concerns.

## Questions

Open a GitHub Discussion or an issue labeled `question` if you need clarification.
