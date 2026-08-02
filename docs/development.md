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
- `shared` → nothing else in the backend tree
- Domain **must not** import config or logging modules
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

| Variable                   | Purpose                                 |
| -------------------------- | --------------------------------------- |
| `NODE_ENV` / `ENVIRONMENT` | `development` \| `test` \| `production` |
| `LOG_LEVEL`                | Logging verbosity                       |

Service-specific schemas should **extend** the baseline, not replace it.

## Testing

| Layer           | Tool   | Location                                     |
| --------------- | ------ | -------------------------------------------- |
| TypeScript unit | Vitest | `*.test.ts` next to source or under `tests/` |
| Python unit     | pytest | `shared/tests/` (more packages later)        |

Run everything with `pnpm test`. Coverage: `pnpm test:coverage`.

Do not add low-value tests that only assert implementation details. Prefer tests that lock invariants of foundation behavior (fail-fast config, error serialization, correlation context).

## Git hooks

Husky runs `lint-staged` on pre-commit (ESLint/Prettier for TS/JS; Ruff/Black for Python). Hooks are installed via the root `prepare` script on `pnpm install`.

## Builds

Library packages emit declarations and JS to `dist/` via `tsc -b` (project references). Workspace runtime resolution currently points at `src/` for fast local iteration; `pnpm build` still verifies emit is clean and deterministic.

## What does not belong in foundation packages

- Domain entities, invariants, or evaluation concepts
- HTTP handlers, Prisma/SQL, queue consumers
- Adapter or Grader logic
- UI components
