# Phase 8.0 — Benchmark Integrity Audit

**Date:** 2026-08-26  
**Branch:** `feat/phase-8-benchmark-integrity`  
**Base SHA (main after Phase 7 merge):** `a4857b275328a2a28d438ca72add160f0bd509e4`  
**Phase 7 PR:** [#21](https://github.com/shreyasvp26/EvalForge/pull/21) — merged into `main` before this branch.

## GitHub synchronization

| Check | Result |
|-------|--------|
| Local working tree | Clean |
| `origin/main` before sync | Phase 6 tip `8fe86f0` (PR #20) |
| Phase 7 PR #21 | Open, MERGEABLE, CI green → **merged** so Phase 8 bases on complete ops surface |
| New branch | `feat/phase-8-benchmark-integrity` pushed from updated `main` |
| Baseline Python tests | Green (domain / application / infrastructure / workers / api) |

## Current architecture (relevant to Phase 8)

### EvaluationRun

- Pins seven versioning axes via `RunPins` (`project`, `case`, `prompt`, `agent`, `adapter`, `platform`, `graders` [+ optional `suite`]).
- Persists `failure_category`, telemetry cost fields, events, artifacts, scores.
- **Gap:** `execution_mode` is **not** on the aggregate/ORM. Provenance hardcodes `execution_mode=None`. Mode lives only in worker env `WORKER_ADAPTER_MODE`.

### Platform version

- `PlatformVersionId` is a typed string wrapper only.
- `runs.platform_version_id` is free text (no FK, no catalog table).
- Create-run validates non-empty only.
- UI default `"platform-1.0.0"` with caption admitting no catalog API.

### Adapter / agent identity

- DB: `Adapter.name` + version labels; **no `adapter_key` column**.
- Runtime: worker `AdapterRegistry` + `normalize_adapter_key(name)`.
- Duplicate normalize maps in worker and `application/run_identity.py` (drift risk).
- Registry currently registers **live** factories for Claude, Cursor, Codex, Gemini, Aider — but only **Gemini CLI** is the proven live production path. Deterministic mode only for Claude synthetic.
- Resolution is fail-closed for unknown names (good); registering unverified live adapters overstates support.

### Benchmark representation

- No first-class `Benchmark` entity.
- **SuiteVersion** (immutable composition of case versions) + immutable Case/Prompt/Grader pins **already express** a reusable benchmark.
- Suite fan-out (`CreateSuiteRuns`) + `AggregateSuiteResults` is the natural execution container.
- Formalize Suite-as-benchmark via API semantics / provenance / comparison — avoid duplicate entity unless proven necessary.

### Provenance (`GET /v1/runs/{id}/provenance`)

- Returns pins, repo URL/SHA, agent/adapter labels + `adapter_key`, graders, scores, telemetry, reproducibility.
- Safe (no secrets) today; `execution_mode` stubbed.
- Needs effective execution config + platform catalog metadata.

### Comparison (`POST /v1/runs/compare`)

- Side-by-side entries + pin deltas vs baseline.
- **Gap:** no explicit **comparability / compatibility** verdict for cross-agent benchmark fairness (same case/SHA/prompt/graders/platform; agent/adapter/mode may differ).

### Frontend

- Run detail shows platform pin as free text; execution mode caption says worker-scoped.
- Compare / provenance clients exist; minimal UI surface — Phase 8 should only expose new fields, no redesign.

## Phase 8 plan (derived from audit)

| Step | Change | Approach |
|------|--------|----------|
| 8.1 | Persist execution configuration | Add `execution_mode` + safe `execution_metadata` on Run; worker records effective values; provenance reads them |
| 8.2 | Platform version catalog | New `platform_versions` entity (immutable published policies); pin FK; validate at create |
| 8.3 | Adapter registry hardening | Authoritative keys; live = Gemini only; deterministic = Claude synthetic; unsupported → fail closed |
| 8.4–8.5 | Benchmark concept + execution | Formalize SuiteVersion as benchmark; strengthen provenance/identifiers; reuse suite execution |
| 8.6 | Cross-agent comparability | Explicit compatibility result on compare |
| 8.7 | Provenance hardening | Full WHAT/WHO/WHERE/HOW; secret redaction tests |
| 8.8–8.11 | Verification | Deterministic Docker E2E; live Gemini if quota; CI green |
| 8.12 | Docs + PR | Architecture docs; open PR; do not merge |

## Explicit non-goals (unchanged)

- Fake Cursor / Codex / Claude live adapters
- Fabricated token/cost telemetry
- Private Git auth
- Broad frontend redesign
- Silent adapter fallbacks
