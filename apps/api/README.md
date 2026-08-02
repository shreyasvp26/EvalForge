# agent-eval-api

EvalForge **Control Plane** — FastAPI HTTP surface over Application use cases.

## Role

Per Backend Architecture §4 / §11 and REST API Design:

| Owns                                              | Must NOT do                                       |
| ------------------------------------------------- | ------------------------------------------------- |
| Request/response translation + shape validation   | Business rules / Domain invariants                |
| Authentication (Bearer → `Actor`)                 | Authorization policy (Application owns that)      |
| Invoking Application `execute(...)`               | SQLAlchemy sessions, repositories, Redis, S3      |
| Mapping Application/shared errors → HTTP          | Importing Domain entities into routers            |
| Correlation IDs, OpenAPI, health/system endpoints | Worker lifecycle use cases (StartRun, Record*, …) |

## Package layout

```
agent_eval_api/
  main.py              # create_app(), lifespan, uvicorn entry
  config.py            # ApiSettings
  composition.py       # ApiContainer — wires Application ← Infrastructure
  dependencies.py      # FastAPI Depends (Actor, services)
  errors.py            # Consistent error schema / handlers
  auth/                # Bearer verification + AllowAllAuthorization stub
  middleware/          # Correlation-ID ASGI middleware
  schemas/             # Pydantic request/response (shape only)
  routers/             # Health, system, v1 resource routers
```

## Request flow

```
Client
  → Correlation middleware (X-Correlation-ID)
  → Auth boundary (Bearer → Actor)          # except /health/*
  → Pydantic shape validation
  → Router builds Command/Query + calls Application use case
  → Application (authorize, UoW, Domain, ports)
  → DTO → response schema
  → HTTP response  |  AppError → { error: { code, message, retryable, details? } }
```

## Dependency injection

`build_api_container()` is the composition root:

1. Load `ApiSettings` (+ Infrastructure settings via `build_infrastructure`)
2. Wire Infrastructure adapters (UoW, queue, ids, events, idempotency)
3. Attach `AllowAllAuthorization` (real Project-scoped policy is TODO)
4. Construct public Application use cases into `ApplicationServices`
5. Lifespan stores `ApiContainer` on `app.state` and disposes on shutdown

Routers depend only on `ApplicationServices` / `Actor` interfaces — never on
Infrastructure types.

## Run locally

```bash
# from repo root
uv sync --all-packages --group dev
export ENVIRONMENT=development
# optional: API_HOST / API_PORT
uv run evalforge-api
# or: uv run uvicorn agent_eval_api.main:create_app --factory --reload
```

OpenAPI: `http://localhost:8000/docs`

## Auth (boundary only)

Send `Authorization: Bearer <actor-id>`. In development/test the token value
_is_ the Actor id (`AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID=true`). Real token
issuance/verification is out of scope for this phase.

Health probes (`/health/live`, `/health/ready`) are intentionally
unauthenticated for orchestrators.

## Tests

```bash
uv run pytest apps/api/tests
```

Tests mock Application services via a `FakeContainer` — **no live database**.

## Endpoint groups

| Group    | Prefix                          |
| -------- | ------------------------------- |
| Health   | `/health/live`, `/health/ready` |
| System   | `/v1/system/info`               |
| Projects | `/v1/projects`                  |
| Suites   | `/v1/suites`                    |
| Cases    | `/v1/cases`                     |
| Prompts  | `/v1/cases/{id}/prompts`        |
| Agents   | `/v1/agents`                    |
| Adapters | `/v1/adapters`                  |
| Graders  | `/v1/graders`                   |
| Runs     | `/v1/runs`                      |
