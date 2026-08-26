# Phase 8 — Benchmark Integrity & Multi-Agent Evaluation

**Branch:** `feat/phase-8-benchmark-integrity`  
**Baseline:** Phase 7 on `main` (PR #21 merged)

## What constitutes a benchmark

EvalForge does **not** introduce a separate `Benchmark` aggregate.

A **benchmark** is the immutable evaluation definition:

```
SuiteVersion (optional container)
  └── CaseVersion (exact repository_url + commit_sha + subdirectory)
        └── PromptVersion (pinned prompt content)
        └── GraderVersion[] (objective / rubric)
  └── PlatformVersion (sandbox / execution / timeout / environment / grading policy)
```

AgentVersion + AdapterVersion + `execution_mode` are **not** part of the
benchmark definition — they are how a particular Run evaluates that definition.

`CreateSuiteRuns` is the canonical benchmark execution entrypoint (fan-out one
Run per composition case through the existing worker). Single-case CreateRun
is the atomic unit.

`benchmark_key` on provenance / comparison is a stable opaque key over the
agent-independent dimensions.

## Immutability

- Case / Prompt / Grader / Suite / Platform versions are DRAFT → ACTIVE → SUPERSEDED.
- Only ACTIVE or SUPERSEDED versions are pinnable.
- Historical Runs keep their pins; publishing V2 never mutates V1 evaluations.

## Agents and adapters

| Key | Deterministic | Live |
|-----|---------------|------|
| `claude_code` | Yes (synthetic NDJSON) | **No** |
| `gemini_cli` | No | **Yes** (canonical) |
| `cursor` / `codex` / `aider` | No | **No** |

Unsupported pins fail with `failure_category=adapter_unsupported`. There is
never a silent fallback to Gemini or Claude.

## Platform versions

Catalog entities (`Platform` + `PlatformVersion`) with immutable string-only
policies (secrets rejected). CreateRun requires a pinnable catalog version.
No FK from `runs.platform_version_id` (legacy free-text rows may exist).

## Execution configuration

Each Run persists effective `execution_mode` (`deterministic` \| `live`) and
allowlisted `execution_metadata` (adapter_key, sandbox_engine, …). Secrets are
never stored. Provenance exposes how the Run was executed.

## Exact repository SHA

CaseVersion pins `commit_sha`. The worker materializes that SHA and verifies
HEAD before the adapter runs. Branch names are not substitutes for SHA.

## Grading workspace

Graders execute against the same sandbox workspace the agent modified.

## Cross-agent comparison

`POST /v1/runs/compare` returns `comparability`:

- **Compatible** when case, prompt, graders, platform, repository URL, and
  commit SHA match.
- Agent / adapter / execution_mode differences are expected and listed.
- Incompatible comparisons still return deltas but mark
  `comparability.compatible=false` so operators do not treat scores as fair.

## Failure semantics

| Outcome | Status | Signal |
|---------|--------|--------|
| Unsupported / live adapter / sandbox / repo / timeout | `failed` | `failure_category` |
| Grader `passed=false` | `completed` | evaluation failure |

## Explicit non-goals retained

- Fake Cursor / Codex / Claude live adapters
- Fabricated token/cost telemetry
- Private Git auth
- Broad frontend redesign
