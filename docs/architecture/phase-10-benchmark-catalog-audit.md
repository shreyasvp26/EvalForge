# Phase 10 — Benchmark Catalog Foundations Audit

## Decision

**Extend Suite / SuiteVersion. Do not introduce BenchmarkV2.**

A published `SuiteVersion` already is the immutable multi-case benchmark definition:

| Product term | Existing aggregate |
|--------------|-------------------|
| Benchmark | `EvaluationSuite` (stable identity) |
| Benchmark version | `SuiteVersion` (immutable composition) |
| Benchmark case | `CaseVersion` membership via `SuiteCompositionEntry` |
| Benchmark execution | `CreateSuiteRuns` → one `Run` per case |
| Benchmark results | `AggregateSuiteResults` |
| Comparability | Phase 8 `benchmark_key` + Phase 9 matrix |

## What already exists

- Domain: `EvaluationSuite`, `SuiteVersion`, pinnable composition of `CaseVersionId`s
- Application: `CreateSuiteRuns`, `AggregateSuiteResults` with execution vs evaluation failure split
- API: `POST /v1/suites/{id}/versions/{vid}/execute`, `GET .../results`
- Worker: CreateRun fan-out via Redis; repository materialization requires exact hex SHA
- Benchmark identity: suite + case + prompt + platform + graders + repo URL + commit SHA
- Frontend: suite list/detail under `/projects/{id}/suites` (not primary nav)

## Gaps Phase 10 must close

1. **Catalog discovery** — operators need “what benchmarks can I run?” (visibility, case counts, categories)
2. **Case metadata** — category / difficulty / tags for discovery (optional for execution)
3. **Execution group scoping** — aggregation today merges *all* runs for a suite version; repeated executes collide
4. **Seeded canonical suite** — credible multi-case composition with real SHAs and objective graders
5. **Thin benchmark API aliases** — product naming without a second model
6. **Frontend** — Benchmarks entry + execute / progress / results (no redesign)
7. **Docs** — authoring, execution, failure semantics, local runbook

## Non-goals (confirmed)

- No `BenchmarkV2` / `EvaluationSet` aggregates
- No marketplace, leaderboards, or fake adapters
- No UI redesign
- No branch/latest pins — exact commit SHA only

## Canonical seed target

- Live-proven task: `evaluations/canonical/calculator-fix` → `shreyasvp26/evalforge-calculator-fix` @ pinned SHA
- Additional tasks: `evaluations/canonical/coding-benchmark-v1/` (multi-task package, published or fixture-backed)

## Implementation order

1. Catalog metadata + migration
2. Execution group on Runs + scoped aggregation
3. Seeded benchmark definitions
4. API catalog / execute / results / matrix surfaces
5. Frontend benchmarks flow
6. Tests + reproducibility docs
