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
| [phase-4-execution-contract-audit.md](./phase-4-execution-contract-audit.md) | Phase 4 real-evaluation contract (audit) |
| [how-evalforge-evaluates-coding-agents.md](./how-evalforge-evaluates-coding-agents.md) | Operator recipe: Case → sandbox → grade |
| [phase-7-evaluation-operations.md](./phase-7-evaluation-operations.md) | SSE, diagnosis, compare, failure categories |
| [phase-8-benchmark-integrity.md](./phase-8-benchmark-integrity.md) | Benchmark identity, platform catalog, adapter matrix |
| [phase-8-benchmark-integrity-audit.md](./phase-8-benchmark-integrity-audit.md) | Phase 8 pre-implementation audit |

Engineering conventions for implementing against these docs live in [../development.md](../development.md).
