# Phase 7 — Evaluation Operations & Observability (Audit)

**Branch:** `feat/phase-7-evaluation-operations`  
**Baseline:** `main` @ Phase 6 merge (`8fe86f0` / PR #20)

This document records the pre-implementation audit. Implementation extends
existing ports; it does not redesign the frontend, rewrite the execution
engine, or fabricate provider telemetry.

## Current state (what already works)

Canonical path remains:

Case Version → pins → Redis → Worker → DockerSandbox → SHA materialization →
Adapter (live Gemini) → workspace grading → structured Scores → suite
aggregation → provenance → UI (polling).

| Area | Status |
|------|--------|
| Durable `execution_events` + REST list | Done |
| Worker `EventPersistencePipeline` + `EventProjector` hooks | Done (SSE not connected) |
| Frontend live UX | Polling @ 2.5s (`useRunPolling`) |
| `FailureCause` (worker) | Exists; persisted only as free-text `failure_reason` |
| COMPLETED + failing score vs FAILED | Correct in domain; UI soft-labels “Failed” |
| Provenance API | Pins + repo SHA + adapter + score rollup |
| `ExecutionCost` columns | Schema + domain exist; **not wired** from workers / API |
| Suite fan-out + rollup | Done; soft exec vs eval split (no `evaluation_failed` counter) |
| Artifacts list + download | Done; no safe body preview |
| Run comparison | Absent |
| Structured failure analysis API | Absent |
| Playwright critical path | Minimal (`e2e/critical-path.spec.ts`) |

## Gaps vs Phase 7 (justified work)

### P0 — Live observability

- Wire `EventProjector` → Redis pub/sub notification after durable persist
- Add authenticated SSE on `GET /v1/runs/{id}/events/stream`
- DB remains source of truth; SSE delivers sequence + terminal signal
- Keep polling fallback; frontend prefers SSE when available
- Auth: Bearer (fetch stream) + optional `access_token` query for EventSource

### P0 — Failure semantics

- Persist structured `failure_category` alongside `failure_reason`
- Align with worker `FailureCause`; add `repository_preparation` where materializer fails
- Keep run statuses unchanged (`failed` ≠ evaluation fail)
- Expose category on Run / provenance / suite case results / UI

### P0 — Telemetry

- Record wall-clock when worker can measure it
- Expose nullable token/cost contract with `provider_usage_available`
- **Never** fabricate Gemini/Groq cost or token counts

### P1 — Suite / comparison / failure / artifacts / reproducibility

- Explicit suite counters: evaluation failed vs execution failed
- Compare runs (and suite versions) via provenance + scores
- Failure diagnosis hierarchy: summary → reason → evidence → events/artifacts
- Safe text/JSON/diff/log preview with size limits
- Enrich provenance for reproduce-without-execute contract

### P2 — Frontend + Playwright

- Extend run cockpit (connection indicator, category, telemetry, diagnosis)
- Do **not** redesign Overview / landing / shell theme
- Expand checked-in Playwright critical path (deterministic; live provider gated)

## Explicit non-goals

- Fake Cursor/Codex/Claude adapters
- Replacing Postgres events with ephemeral streams
- New queue / sandbox implementation
- Mandatory live Gemini in CI
- Statistical “significance” claims without sample size
- Frontend visual redesign

## Extension points (prefer these)

1. `FailRunCommand` / `EvaluationRun.fail` / `RunOrm` — add `failure_category`
2. `ApplicationRunStatus.project_failed` — pass cause through
3. `ExecutionCost` + new `RecordRunTelemetry` / complete-path wall clock
4. `ProjectionHub` + new `RedisRunEventFanout` (mirror cancel store pattern)
5. `apps/api/.../routers/v1/runs.py` — SSE beside existing list endpoint
6. `AggregateSuiteResults` / `SuiteAggregateDTO` — evaluation_failed counters
7. New application use cases: compare runs, diagnose failure, artifact preview
8. `useRunPolling` — SSE invalidate + polling fallback (comment already anticipates)
9. `apps/web/e2e/critical-path.spec.ts` — extend coverage

## Implementation order

1. Audit commit (this doc)
2. Failure category persistence + API
3. Telemetry contract + wall-clock recording
4. Redis fan-out + SSE + tests
5. Suite analytics clarity
6. Run comparison + failure analysis
7. Artifact preview + reproducibility enrichment
8. Frontend integration
9. Playwright + docs + Docker verification
