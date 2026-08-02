# API documentation

## Control Plane foundation (Phase 6A)

The public HTTP API for EvalForge lives in `apps/api` (`agent_eval_api`).

**Phase 6A** delivers the Control Plane foundation only:

- Application factory + lifespan
- Composition root / DI
- Middleware (correlation, timing, structured request logging)
- Exception mapping
- Authentication boundary
- OpenAPI
- Health / readiness
- Versioned `/v1` root

**Phase 6B** adds business resource endpoints (Projects, Suites, Cases, Agents,
Graders, Runs).

Architecture authorities:

- [Backend Architecture](../architecture/backend-architecture.md)
- [REST API Design](../architecture/rest-api-design.md)

Implementation README: [`apps/api/README.md`](../../apps/api/README.md)

## Request flow

1. Correlation ID bound/echoed (`X-Correlation-ID`)
2. Timing recorded (`X-Request-Duration-Ms`)
3. Structured request log (method, path, status, duration)
4. Bearer authentication → `Actor` (except health probes)
5. Router → Application use case (from Phase 6B)
6. Error envelope on failure (no stack traces)

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

## Out of scope until later

- Business CRUD routes (Phase 6B)
- Real JWT / OAuth verification
- Project-scoped authorization policies
- SSE run progress
- Cursor pagination
