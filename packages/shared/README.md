# @agent-eval/shared

Barrel re-exports of the TypeScript foundation packages:

- `@agent-eval/errors`
- `@agent-eval/env`
- `@agent-eval/logger`
- `@agent-eval/utils`

## Why

Backend Architecture places cross-cutting concerns in `shared/`. On the TypeScript side we keep those concerns as focused packages (clear dependency graphs, smaller install surfaces) and expose this barrel for convenience.

Prefer direct imports from the specific package in new code.
