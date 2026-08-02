# @agent-eval/utils

Small set of genuinely cross-cutting TypeScript helpers.

## Why

Helpers that every package needs (exhaustiveness checks, correlation IDs, invariants) belong in one place. Domain-specific helpers do **not** belong here — keep this package intentionally boring and small.

## Included

- `assertNever` / `invariant`
- `isNonEmptyString` / `isUuid`
- `createCorrelationId`
- `sleep`
