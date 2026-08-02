# agent-eval-application

Application Layer for EvalForge.

## Why

Per Backend Architecture §4 / §5 / §11, this package owns **use-case orchestration**:
authorization at the operation level, transaction boundaries (Unit of Work),
coordination of Domain aggregates, idempotency for use-case invocation, and
translation of Domain errors for callers.

It depends on `domain` and `shared` only. It must **not** import FastAPI,
SQLAlchemy, Redis, Celery, HTTP, or any concrete Infrastructure module.

Infrastructure implements the ports defined here (and Domain repository
Protocols); API and Workers invoke the use cases defined here.

## Responsibilities

| Owns                                                            | Must NOT do                               |
| --------------------------------------------------------------- | ----------------------------------------- |
| Use cases / application services                                | Domain invariants (delegate to Domain)    |
| Transaction boundaries via Unit of Work                         | SQL, ORM, queue broker details            |
| Authorization (Project-scoped)                                  | Authentication / HTTP transport           |
| Domain event dispatch _through abstractions_                    | Logging implementations or config loading |
| Idempotency of use-case invocation                              | Adapter / Grader _implementations_        |
| Application contracts (queue, outbox/dispatcher, ID generation) | Business rules that belong on aggregates  |

## Package layout

```
agent_eval_application/
  ports/          # Unit of Work, event dispatcher, queue, auth, idempotency
  commands/       # Write-side input messages
  queries/        # Read-side input messages
  dto/            # Boundary DTOs returned to API / Workers
  use_cases/      # Orchestration services
  common/         # Actor, ID generation, result helpers
  errors.py       # Application errors + Domain error translation
```

## Testing

Unit tests mock ports (Unit of Work, repositories, dispatcher, queue). They
never touch a real database or broker. Prefer `uv run pytest application/tests`.
