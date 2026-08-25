# Phase 6 — Evaluation Engine Plan (Audit)

**Branch:** `feat/phase-6-evaluation-engine`  
**Baseline:** `main` @ Phase 5 merge (live Gemini evaluation path)

This document records the pre-implementation audit. Implementation extends
existing ports; it does not redesign the frontend, add SSE, or rewrite the
execution architecture.

## Current state (what already works)

Canonical CreateRun → Redis → Worker → DockerSandbox → SHA materialization →
adapter → workspace grading → Score → terminal status is production-shaped
(Phase 4–5).

| Area | Status |
|------|--------|
| Domain pins (7 axes + optional suite) | Solid |
| Objective graders (test, exit, file, diff, JSON, lint, build) | Implemented |
| Workspace pytest against agent workspace | Phase 5 |
| Gemini CLI live adapter | Canonical v1 coding agent |
| Fail-closed adapter resolution | Implemented |
| Rubric grader SDK + Anthropic/OpenAI/Gemini judges | Library only |
| Production worker `rubric_factory` | **Not wired** — rubric pins fail closed |
| Groq judge | Documented reserved; **not implemented** |
| Suite CRUD + optional suite pin on Run | Exists |
| Suite fan-out / aggregate results | **Missing** |
| Backend score aggregation policy | **Missing** (UI `runPassSignal` only) |
| `platform_version_id` | Free-text (keep; enrich provenance) |
| Execution mode on Run row | Worker-scoped only |

## Extension points (prefer these)

1. **`PinBasedGraderResolver.rubric_factory`** + parse
   `GraderVersion.specification` → `RubricSpecification`
2. **`create_judge_provider`** + new `providers/groq/` (OpenAI-compatible)
3. **`process.py`** — wire optional judge from `JUDGE_PROVIDER` / env keys
4. **Application** — `CreateSuiteRuns` + `AggregateSuiteResults` over existing
   `CreateRun` / run list
5. **Run provenance read model** — join pins + case repo + adapter name;
   optional execution-identity event metadata (no secrets)
6. **Score aggregation helper** — objective hard-fail policy; no silent weighting

## Explicit non-goals

- Frontend redesign, SSE, analytics, billing, marketplace, SSO
- Fake Cursor/Codex/Claude coding-agent implementations
- Schema rewrite / platform version catalog UI
- Making Groq or any judge mandatory for objective evaluations
- Destabilizing Gemini live path or `EVALFORGE_LIVE_GEMINI_DOCKER` gate

## Acceptance mapping

| Criterion | Approach |
|-----------|----------|
| Structured grader results | Normalize Score `detail` (family, score, max, reason, evidence) |
| Rubric never silently skipped | Keep fail-closed; actionable reason + optional judge wiring |
| Groq | Implement if OpenAI-compatible path stays small |
| Suites executable | Fan-out CreateRun per composition entry + aggregate DTO |
| Reproducibility | Provenance API/DTO; exact SHA remains mandatory |
| E2E | Deterministic worker path + Docker when available; live Gemini gated |

## Implementation order

1. Audit commit (this doc)
2. Structured objective/rubric result contract
3. Production judge wiring + structured judge validation hardening
4. Groq provider (`GROQ_API_KEY`, `GRAQ_API_KEY` alias)
5. Run provenance + aggregation policy
6. Suite execution + aggregation
7. E2E / failure-path tests
8. Architecture doc update (`how-evalforge-evaluates-coding-agents.md`)
