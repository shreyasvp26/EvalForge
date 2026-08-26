# Phase 11 — Real Benchmark Execution Audit

## Prerequisites (done)

- Phase 10 PR #25 merged → `f4c3754` on `main`
- Branch: `feat/phase-11-real-benchmark-execution`

## Architecture decision

**Do not invent a new Benchmark aggregate.** Reuse:

- `CreateSuiteRuns` + `execution_group_id`
- `AggregateSuiteResults`
- `/v1/benchmarks` aliases
- Worker Redis claim + Docker sandbox + `gemini_cli`
- Existing SSE per run (multiplex from results page if needed)

## Gaps to close

1. **Execution UX** — replace pasted IDs with agent/adapter/platform selectors + review step (reuse `runs/new` patterns).
2. **Results UX** — case titles, clearer progress, aggregate semantics, run cockpit links.
3. **Concurrency** — explicit `WORKER_CONCURRENCY` (safe default 1); document fan-out vs in-flight.
4. **Live proof** — Docker health, single-case Gemini, then 5-case Coding Benchmark v1 (or honest provider-blocked).
5. **Seed/run script** — operator path for `SeedCodingBenchmarkV1` + execute.
6. **Playwright** — catalog → configure → review path (deterministic; live separate).
7. **Docs** — execution workflow, failure semantics, concurrency, Gemini config.

## Non-goals

No marketplace, billing, Cursor/Codex live adapters, Redis rewrite, Docker rewrite, or UI redesign.
