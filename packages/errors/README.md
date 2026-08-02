# @agent-eval/errors

Typed error hierarchy for EvalForge.

## Why

Backend Architecture §9 requires distinguishing **domain/application** failures from **infrastructure** failures, and never silently swallowing unexpected errors. A shared hierarchy gives every layer the same vocabulary without coupling to HTTP status codes or ORM exceptions.

## Exports

- `AppError` — abstract base with `code`, `details`, `retryable`, `toJSON()`
- `ApplicationError` — expected use-case failures (not retried by default)
- `InfrastructureError` — DB/queue/storage/network (may be retryable)
- `ValidationError` — shape/semantic validation failures
- `ConfigurationError` — invalid environment at startup (fail fast)
- `serializeError` / `isAppError` — boundary helpers

No business-specific error codes live here yet.
