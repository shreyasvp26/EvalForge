# Architecture

Architecture documents are the **source of truth** for EvalForge system design.

| Document | Scope |
|----------|-------|
| [system-overview.md](./system-overview.md) | Planes, constraints, observability |
| [backend-architecture.md](./backend-architecture.md) | Modules, dependency rules, `shared/` |
| [domain-models.md](./domain-models.md) | Ubiquitous language and entities |
| [rest-api-design.md](./rest-api-design.md) | HTTP/SSE contracts |
| [database-design.md](./database-design.md) | Persistence strategy |
| [schema-design.md](./schema-design.md) | Schema shapes |
| [execution-engine-architecture.md](./execution-engine-architecture.md) | Run orchestration |
| [adaptar-architecture.md](./adaptar-architecture.md) | Agent adapters |
| [grader-architecture.md](./grader-architecture.md) | Graders |

Engineering conventions for implementing against these docs live in [../development.md](../development.md).
