# Docker deployment

Production-ready Compose stack for EvalForge Control Plane + workers.

## Services

| Service      | Role                                             |
| ------------ | ------------------------------------------------ |
| `postgres`   | Primary datastore (persistent `pgdata`)          |
| `redis`      | Run queue + idempotency (persistent `redisdata`) |
| `minio`      | S3-compatible artifact store (`miniodata`)       |
| `minio-init` | Creates the artifact bucket once                 |
| `migrate`    | One-shot `alembic upgrade head`                  |
| `api`        | Control Plane (`evalforge-api`, port 8000)       |
| `workers`    | Execution Plane claim loop (`evalforge-worker`)  |

Startup order is enforced with healthchecks and `depends_on` conditions:
postgres / redis / minio healthy → migrate + bucket init complete → api healthy → workers.

## Quick start

From the **repository root**:

```bash
cp .env.example .env
# Set a strong JWT_SECRET_KEY before production use.

docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up --build
```

API:

- Live: http://localhost:8000/health/live
- Ready: http://localhost:8000/health/ready
- Metrics: http://localhost:8000/metrics
- OpenAPI: http://localhost:8000/docs

## Images

| File                 | Image                        |
| -------------------- | ---------------------------- |
| `Dockerfile.api`     | API + Alembic migrate runner |
| `Dockerfile.workers` | Background worker process    |

Build context is the monorepo root (workspace packages + `uv.lock`).

## Notes

- Workers claim from Redis via `RedisWorkerQueue`. The default process entry uses
  the chassis lifecycle factory; attach the production harness (Sandbox /
  Adapter / Graders) for full execution in your environment.
- Mount the Docker socket into `workers` when running real Sandbox executions.
- Web UI image remains deferred (`Dockerfile.web.placeholder`).
