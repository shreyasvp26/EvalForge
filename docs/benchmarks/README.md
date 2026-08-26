# Benchmark Catalog & Reproducible Evaluation

EvalForge treats a **published SuiteVersion** as an immutable benchmark definition.
There is no second “BenchmarkV2” aggregate.

## Concepts

| Product term        | Aggregate                                                           |
| ------------------- | ------------------------------------------------------------------- |
| Benchmark           | `EvaluationSuite` (`catalog_key`, `catalog_visible`)                |
| Benchmark version   | Published `SuiteVersion`                                            |
| Benchmark case      | `CaseVersion` in suite composition                                  |
| Benchmark execution | `CreateSuiteRuns` → one `Run` per case, shared `execution_group_id` |
| Results             | `AggregateSuiteResults` (optionally scoped by `execution_group_id`) |

## Immutability rules

- Pin **exact commit SHAs** (7–40 hex). Branch tips (`main`, `master`, `latest`) are rejected.
- Execute only **published** CaseVersions / PromptVersions / GraderVersions / PlatformVersions.
- Changing a case, prompt, grader, or platform → create a new version. Never mutate history.

## Canonical suite: Coding Benchmark v1

Repository: `https://github.com/shreyasvp26/evalforge-coding-benchmark-v1.git`  
Pinned SHA: `47329c4885c2855072b15aaee227f5b92416301f`

| Case                        | Category  | Difficulty | Subdirectory              | Grader           |
| --------------------------- | --------- | ---------- | ------------------------- | ---------------- |
| Fix arithmetic bug          | bugfix    | easy       | `tasks/01-calculator-add` | workspace pytest |
| Fix Fibonacci off-by-one    | bugfix    | easy       | `tasks/02-fibonacci`      | workspace pytest |
| Implement dict merge        | feature   | easy       | `tasks/03-merge-dicts`    | workspace pytest |
| Fix CSV empty-field parsing | edge-case | medium     | `tasks/04-parse-csv`      | workspace pytest |
| Fix clamp upper bound       | bugfix    | easy       | `tasks/05-clamp`          | workspace pytest |

Definitions: `application/.../benchmark_catalog.py`  
Seed use case: `SeedCodingBenchmarkV1`

## API

Catalog (aliases over suites):

- `GET /v1/benchmarks?project_id=`
- `GET /v1/benchmarks/{suite_id}`
- `GET /v1/benchmarks/{suite_id}/versions`
- `POST /v1/benchmarks/{suite_id}/versions/{version_id}/execute`
- `GET /v1/benchmarks/{suite_id}/versions/{version_id}/results?execution_group_id=`

Suite surfaces remain authoritative (`/v1/suites/...`).

## Execution & aggregation

1. Validate every composition entry (published case, SHA, prompt, graders, platform).
2. Generate `execution_group_id` and create one queued Run per case via existing Redis/worker path.
3. Aggregate with `execution_group_id` so repeated executes do not mix.

**Execution failure** (`status=failed`): timeout, provider, sandbox, adapter, credential, repository.  
**Evaluation failure** (`status=completed` and `passed=false`): agent ran; graders failed.

Pass rate excludes execution failures from the denominator.

## Adapter comparison

Keep the benchmark constant. Only agent/adapter/execution_mode may vary.
Use Phase 8/9 `benchmark_key` + `POST /v1/runs/benchmark-matrix`.

## Adding a case

1. Author a small deterministic task under `evaluations/canonical/...`.
2. Publish the package to a public git repo and record the exact SHA.
3. Create Case + Prompt + CaseVersion (subdirectory if monorepo) with objective grader.
4. Publish versions; add CaseVersion to a new SuiteVersion; publish suite.
5. Mark suite `catalog_visible=true`.

## Local seed (application tests)

```bash
uv run pytest application/tests/test_seed_coding_benchmark.py -q
```
