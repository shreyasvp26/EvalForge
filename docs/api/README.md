# API documentation

## Control Plane

The public HTTP API for EvalForge lives in `apps/api` (`agent_eval_api`).

Architecture authorities:

- [Backend Architecture](../architecture/backend-architecture.md) — API Layer responsibilities and dependency rules
- [REST API Design](../architecture/rest-api-design.md) — resource model, auth split, error model, idempotency

Implementation README: [`apps/api/README.md`](../../apps/api/README.md)

## Request flow

1. **Transport** — HTTP request hits FastAPI; correlation id bound/echoed.
2. **Authenticate** — Bearer credential verified at the API boundary → `Actor`.
3. **Validate shape** — Pydantic models reject malformed bodies (422).
4. **Translate** — Router builds an Application Command/Query and calls `execute`.
5. **Authorize + orchestrate** — Application Layer (not the API) enforces Project scope and Domain rules.
6. **Respond** — DTOs serialize to response schemas; Application errors map to a single error envelope.

```
Client → API (auth + shape) → Application (authz + UoW) → Domain → Infrastructure ports
```

## Error envelope

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "…",
    "retryable": false,
    "details": {}
  }
}
```

No stack traces are returned. Unexpected failures use `INTERNAL_ERROR` (500).

## OpenAPI

Generated at runtime: `GET /openapi.json`, interactive docs at `/docs`.

## Out of scope (later)

- Real JWT / OAuth token verification
- Project-scoped authorization policies (beyond AllowAll stub)
- SSE run progress streams
- Cursor pagination metadata
- Dedicated list/get queries for Execution Events / Artifacts / Audit Logs
