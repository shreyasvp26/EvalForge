# agent-eval-api

EvalForge **Control Plane** — FastAPI HTTP foundation (Phase 6A).

## Scope (Phase 6A)

Foundation only. **No business resource endpoints yet** (Projects, Suites,
Cases, Agents, Graders, Runs arrive in Phase 6B).

| Owns                                              | Must NOT do                                    |
| ------------------------------------------------- | ---------------------------------------------- |
| Application factory, lifespan, OpenAPI            | Business CRUD routes                           |
| Composition root + Application use-case factories | SQLAlchemy / Redis / S3 in routers             |
| Bearer → `Actor` auth boundary                    | Authorization _policy_ (Application owns that) |
| Correlation, timing, structured request logging   | Domain entities in routers                     |
| Centralized error → HTTP mapping                  | Instantiating repositories in handlers         |
| Health / readiness                                |                                                |

## Package layout

```
agent_eval_api/
  main.py              # create_app(), lifespan, uvicorn entry
  config.py            # ApiSettings
  composition.py       # ApiContainer + build_application_services()
  dependencies.py      # FastAPI Depends (Actor, services, settings)
  errors.py            # Consistent error schema / handlers
  auth/                # Bearer verification + AllowAllAuthorization
  middleware/          # Correlation, timing, request logging
  schemas/             # Health / error shapes
  routers/             # health, /v1 root, system
```

## Request flow

```
Client
  → Correlation middleware (X-Correlation-ID)
  → Timing middleware (X-Request-Duration-Ms)
  → Structured request logging
  → Auth boundary (Bearer → Actor)   # except /health/*
  → Router (foundation only in 6A)
  → Application services (wired; used from 6B)
```

## Dependency injection

`build_api_container()`:

1. Load `ApiSettings` + `build_infrastructure(...)`
2. Attach `AllowAllAuthorization` (real Project-scoped policy is TODO)
3. `build_application_services(...)` constructs use cases from Infrastructure ports
4. Lifespan stores `ApiContainer` on `app.state` and disposes on shutdown

Routers must never open repositories or sessions — only consume
`ApplicationServices` via Depends (Phase 6B).

## Health

| Endpoint            | Auth | Purpose                                      |
| ------------------- | ---- | -------------------------------------------- |
| `GET /health/live`  | no   | Process up                                   |
| `GET /health/ready` | no   | Composition present + Infrastructure healthy |

## Versioned root

`GET /v1` — foundation marker. Business paths under `/v1/...` land in 6B.
`GET /v1/system/info` — authenticated process metadata.

## Auth (boundary only)

`Authorization: Bearer <actor-id>` (dev: token value is the Actor id).

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

Foundation tests mock Infrastructure via `FakeContainer` where appropriate;
DI tests exercise `build_infrastructure(profile=MEMORY)`.
