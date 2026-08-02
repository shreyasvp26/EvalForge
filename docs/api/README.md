# API documentation

## Control Plane REST API (Phase 6B)

The public HTTP API for EvalForge lives in `apps/api` (`agent_eval_api`).

**Phase 6A** delivered the foundation (factory, DI, middleware, errors, auth
boundary, health, OpenAPI).

**Phase 6B** exposes the Application layer over versioned REST:

- Projects, Suites, Cases, Prompt Versions, Case Versions
- Agents, Adapters, Graders
- Runs + nested Events, Artifacts, Scores

Architecture authorities:

- [Backend Architecture](../architecture/backend-architecture.md)
- [REST API Design](../architecture/rest-api-design.md)

Implementation README: [`apps/api/README.md`](../../apps/api/README.md)

## Request flow

1. Correlation ID bound/echoed (`X-Correlation-ID`)
2. Timing recorded (`X-Request-Duration-Ms`)
3. Structured request log (method, path, status, duration)
4. Bearer authentication → `Actor` (except health probes)
5. Router builds Command/Query → Application use case → Pydantic response
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

## Remaining after Phase 6

- Real JWT / OAuth verification
- Project-scoped authorization policies (beyond `AllowAllAuthorization`)
- SSE run progress
- Cursor pagination
- Audit log endpoints
- Score cross-run queries by Grader
