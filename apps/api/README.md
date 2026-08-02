# agent-eval-api

EvalForge **Control Plane** — FastAPI REST API (Phase 6B).

## Scope

Versioned business resource endpoints over Application use cases. Routers
construct Commands/Queries, invoke use cases, map DTOs → Pydantic schemas, and
return HTTP responses. They never touch repositories, SQLAlchemy, Redis, or
Domain entities.

| Owns                                              | Must NOT do                            |
| ------------------------------------------------- | -------------------------------------- |
| Application factory, lifespan, OpenAPI            | Business rules / Domain invariants     |
| Composition root + Application use-case factories | SQLAlchemy / Redis / S3 in routers     |
| Bearer → `Actor` auth boundary                    | Domain entities in routers             |
| Project RBAC (`AuthorizationPort` adapter)        | Instantiating repositories in handlers |
| Correlation, timing, structured request logging   | Exposing Application DTOs directly     |
| Centralized error → HTTP mapping                  | Business rules in middleware           |
| Health / readiness + `/v1` business resources     | Wiring workers into routers            |

## Package layout

```
agent_eval_api/
  main.py              # create_app(), lifespan, uvicorn entry
  config.py            # ApiSettings
  composition.py       # ApiContainer + build_application_services()
  dependencies.py      # FastAPI Depends (Actor, services, settings)
  errors.py            # Consistent error schema / handlers
  auth/                # JWT Bearer + ProjectRbacAuthorization
  middleware/          # Correlation, timing, request logging
  schemas/             # Pydantic request/response models
  routers/
    health.py, system.py, v1_root.py
    v1/                # projects, suites, cases, prompts, agents,
                       # adapters, graders, runs
```

## Request flow

```
Client
  → Correlation middleware (X-Correlation-ID)
  → Timing middleware (X-Request-Duration-Ms)
  → Structured request logging
  → Auth boundary (Bearer → Actor)   # except /health/*
  → Router (Command/Query + schema map)
  → Application use case
```

## API surface (v1)

| Resource        | Collection                     | Nested / actions                                 |
| --------------- | ------------------------------ | ------------------------------------------------ |
| Projects        | `GET/POST /v1/projects`        | get, rename (PATCH), settings (PATCH), deprecate |
| Suites          | `GET/POST /v1/suites`          | versions, publish, retire, deprecate             |
| Cases           | `GET/POST /v1/cases`           | versions, publish, deprecate                     |
| Prompt Versions | under `/v1/cases/{id}/prompts` | draft + publish                                  |
| Agents          | `GET/POST /v1/agents`          | versions + publish                               |
| Adapters        | `GET/POST /v1/adapters`        | get, versions + publish                          |
| Graders         | `GET/POST /v1/graders`         | versions + publish                               |
| Runs            | `GET/POST /v1/runs`            | cancel; nested `events`, `artifacts`, `scores`   |

Creates return **201**. State transitions (deprecate / publish / cancel) use
**POST**. Lists return `{ items, count }`.

## Idempotency

`Idempotency-Key` header on resource-creating POSTs (`projects`, `suites`,
`cases`, `agents`, `adapters`, `graders`, `runs`). Forwarded to Application
`idempotency_key` — never accepted in the JSON body.

## Auth

`Authorization: Bearer <jwt>` where the JWT `sub` claim is the Actor id.
Set `JWT_SECRET_KEY` (required unless `AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID=true`).

Authorization uses project-aware RBAC (`Owner` / `Admin` / `Maintainer` /
`Viewer`) via `ProjectRbacAuthorization`. Membership rows live in Infrastructure;
creating a Project grants the caller `Owner`. Application use cases are unchanged.

## Run locally

```bash
uv sync --all-packages --group dev
uv run evalforge-api
# OpenAPI: http://localhost:8000/docs
```

## Tests

```bash
uv run pytest apps/api/tests
```

Tests use `TestClient` + `FakeContainer` / mocked `ApplicationServices` — no
real database.
