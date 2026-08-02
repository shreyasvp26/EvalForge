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

## Read surface

Every future REST resource is served through Application query use cases that
return frozen DTOs only (never Domain entities). Catalog and project reads:

| Use case                           | Query                                   | Returns                           |
| ---------------------------------- | --------------------------------------- | --------------------------------- |
| `GetProject` / `ListProjects`      | `GetProjectQuery` / `ListProjectsQuery` | `ProjectDTO` / `list[ProjectDTO]` |
| `GetSuite` / `ListSuitesByProject` | …                                       | `SuiteDTO` / `list[SuiteDTO]`     |
| `GetCase` / `ListCasesByProject`   | …                                       | `CaseDTO` / `list[CaseDTO]`       |
| `GetAgent` / `ListAgents`          | …                                       | `AgentDTO` / `list[AgentDTO]`     |
| `GetAdapter` / `ListAdapters`      | …                                       | `AdapterDTO` / `list[AdapterDTO]` |
| `GetGrader` / `ListGraders`        | …                                       | `GraderDTO` / `list[GraderDTO]`   |
| `GetRun` / `ListRunsByProject`     | …                                       | `RunDTO` / `list[RunDTO]`         |

Run nested reads (owned by the Run aggregate; no separate event/artifact repos):

| Use case          | Query                  | Returns                   |
| ----------------- | ---------------------- | ------------------------- |
| `GetRunEvents`    | `GetRunEventsQuery`    | `list[ExecutionEventDTO]` |
| `GetRunArtifacts` | `GetRunArtifactsQuery` | `list[ArtifactDTO]`       |
| `GetRunScores`    | `GetRunScoresQuery`    | `list[ScoreDTO]`          |

`ListProjects` filters by `ensure_can_access_project` per row. Platform catalog
lists (`ListAgents` / `ListAdapters` / `ListGraders`) gate on
`ensure_can_create_project`. Run nested reads authorize via the Run's pinned
`project_id`.

Repository support for catalog/project listing: Domain `list_all()` on
`ProjectRepository`, `AgentRepository`, `AdapterRepository`, and
`GraderRepository` (Infrastructure + in-memory test fakes implement it).

## Testing

Unit tests mock ports (Unit of Work, repositories, dispatcher, queue). They
never touch a real database or broker. Prefer `uv run pytest application/tests`.
In-memory harness: `SharedStore`, `InMemoryUnitOfWorkFactory`, auth fakes in
`tests/fakes.py`. Read-query coverage lives in `tests/test_read_queries.py`.
