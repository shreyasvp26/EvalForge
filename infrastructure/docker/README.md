# Docker scaffolding

Local development compose and Dockerfile placeholders live here.

- `docker-compose.yml` — empty compose file ready for local services
- `Dockerfile.*.placeholder` — reserved paths for API, web, and workers images

## Planned services (later phases)

| Service    | Dockerfile           | Notes             |
| ---------- | -------------------- | ----------------- |
| `api`      | `Dockerfile.api`     | HTTP API          |
| `web`      | `Dockerfile.web`     | Web app           |
| `workers`  | `Dockerfile.workers` | Background jobs   |
| `postgres` | (official image)     | Primary datastore |

Do not add production Dockerfiles in Phase 0.
