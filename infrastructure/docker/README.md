# Docker deployment

Production-ready Compose stack for EvalForge Control Plane + workers + web.

## Services

| Service         | Role                                               |
| --------------- | -------------------------------------------------- |
| `postgres`      | Primary datastore (persistent `pgdata`)            |
| `redis`         | Run queue + idempotency + cancel signals           |
| `minio`         | S3-compatible artifact store (`miniodata`)         |
| `minio-init`    | Creates the artifact bucket once                   |
| `sandbox-image` | Builds `evalforge/sandbox:local` for DockerSandbox |
| `migrate`       | One-shot `alembic upgrade head`                    |
| `api`           | Control Plane (`evalforge-api`, port 8000)         |
| `workers`       | Execution Plane claim loop (`evalforge-worker`)    |
| `web`           | Next.js UI (port 3000)                             |

Startup order is enforced with healthchecks and `depends_on` conditions:
postgres / redis / minio healthy → migrate + bucket init + sandbox image → api healthy → workers + web.

## Quick start

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

From the **repository root**:

```bash
cp .env.example .env
# Set a strong JWT_SECRET_KEY before production use.

docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up --build
```

Verify:

```bash
curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
open http://localhost:3000
```

Stop:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --env-file .env down
# Add -v only when you intentionally want to wipe Postgres/Redis/MinIO volumes.
```

## Images

| File                 | Image                           |
| -------------------- | ------------------------------- |
| `Dockerfile.api`     | API + Alembic migrate runner    |
| `Dockerfile.workers` | Background worker process       |
| `Dockerfile.sandbox` | Agent sandbox (`DockerSandbox`) |
| `Dockerfile.web`     | Next.js standalone UI           |

Build context is the monorepo root (workspace packages + `uv.lock` / `pnpm-lock.yaml`).

## Execution modes

Compose workers default to **real Docker** + **deterministic Claude adapter**:

| Variable                | Compose default           | Meaning                                                                   |
| ----------------------- | ------------------------- | ------------------------------------------------------------------------- |
| `WORKER_SANDBOX_ENGINE` | `docker`                  | Real `DockerPyEngine` via mounted Docker socket                           |
| `WORKER_ADAPTER_MODE`   | `deterministic`           | `ClaudeCodeAdapter` with injected NDJSON stream (no provider credentials) |
| `WORKER_SANDBOX_IMAGE`  | `evalforge/sandbox:local` | Image built by `sandbox-image` service                                    |

### Real Claude CLI (optional)

1. Build sandbox with CLI: `EVALFORGE_INSTALL_CLAUDE_CLI=1`
2. Set `ANTHROPIC_API_KEY` in `.env` (never commit it)
3. Set `WORKER_ADAPTER_MODE=claude`
4. Set `WORKER_SANDBOX_NETWORK=bridge` so the sandbox can reach Anthropic

Deterministic / FakeDocker remain available for unit tests (`WORKER_SANDBOX_ENGINE=fake`).

## Artifacts

Workers upload artifact bytes to MinIO and persist metadata in Postgres.
Download: `GET /v1/runs/{run_id}/artifacts/{artifact_id}/content`.

## Cancellation

`POST /v1/runs/{run_id}/cancel` updates Domain status, publishes a Redis cancel
signal (`RUN_CANCEL_KEY_PREFIX`), and removes the run from the pending queue when
still queued. Workers observe the signal cooperatively and tear down the sandbox.

## Troubleshooting

| Symptom                            | Check                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------- |
| Workers fall back / fail on Docker | Docker Desktop running; socket mounted; `WORKER_SANDBOX_ENGINE=docker`    |
| Migrations fail                    | `migrate` logs; `DATABASE_URL` must use host `postgres` inside Compose    |
| Redis unavailable                  | `redis` healthy; `REDIS_URL=redis://redis:6379/0` in Compose              |
| Claude live mode fails             | CLI installed in sandbox image; `ANTHROPIC_API_KEY` set; network `bridge` |
| Sandbox timeout                    | `WORKER_EXECUTION_TIMEOUT_SECONDS`; worker + Docker logs                  |
| Worker not consuming               | `docker compose logs workers`; Redis pending list; API enqueue errors     |

See also `docs/development.md` and `workers/README.md`.
