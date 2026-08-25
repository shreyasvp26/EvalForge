# Phase 7 — Evaluation Operations & Observability

**Branch:** `feat/phase-7-evaluation-operations`  
**PR:** #21  
**Baseline:** Phase 6 evaluation engine on `main`

## What operators can answer now

1. What was evaluated — provenance pins + repo SHA  
2. Exact revision — `commit_sha` on provenance / reproduce contract  
3. Prompt / agent / adapter / grader versions — provenance summaries  
4. What happened — durable events + SSE live delivery  
5. Why pass/fail — diagnosis hierarchy + failure_category  
6. Scores & evidence — structured grader results + diagnosis evidence  
7. Suite/benchmark performance — evaluation vs execution failure counters  
8. Compare runs — `POST /v1/runs/compare`  
9. Inspect failures/artifacts — diagnosis + safe artifact preview  
10. Live monitor — SSE with polling fallback  
11. Reproduce — provenance `reproducibility` block (no auto-execute, no secrets)  
12. Execution vs evaluation failure — status `failed` vs completed + `passed=false`

## Architecture (delivery vs truth)

```
Worker → persist execution_event (Postgres)
      → Redis pub/sub notify (optional wake)
API  → GET /events (authoritative list)
     → GET /events/stream (SSE; replays DB; closes on terminal)
UI   → EventSource → invalidate React Query
     → polling fallback @ 2.5s when SSE down
```

SSE is **not** the source of truth. Reconnect uses `Last-Event-ID` / `after_sequence`.

## Failure semantics

| Outcome | Run status | Category / signal |
|---------|------------|-------------------|
| Adapter / sandbox / repo / timeout / worker | `failed` | `failure_category` enum |
| Pre-running fail from queued | often `cancelled` | reason text |
| Agent finished; grader failed | `completed` | score `passed=false` / diagnosis `evaluation_failure` |

## Telemetry contract

- `wall_clock_ms` / `compute_ms` when recorded by worker  
- `input_tokens` / `output_tokens` / `estimated_cost` only when `provider_usage_available=true`  
- Never fabricate Gemini/Groq cost  

## Key APIs added/extended

- `GET /v1/runs/{id}/events/stream`  
- `GET /v1/runs/{id}/diagnosis`  
- `POST /v1/runs/compare`  
- `GET /v1/runs/{id}/artifacts/{aid}/preview`  
- Provenance + suite aggregate enrichment  
- `failure_category` + `telemetry` on run responses  

## Explicit non-goals retained

- Fake Cursor/Codex/Claude adapters  
- Mandatory live Gemini in CI  
- Frontend visual redesign  
- Statistical significance claims  
