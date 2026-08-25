# How EvalForge evaluates a coding agent

This document describes the **Phase 6 evaluation / benchmarking engine**:
reusable cases, pinned versions, objective + judge grading, suite fan-out, and
inspectable provenance — without redesigning the Phase 5 Gemini live path.

## Target contract

```
Project
  → Case Version (immutable after publish)
      ├── Prompt Version (exact content)
      ├── repository_url + exact commit_sha (+ optional subdirectory)
      ├── applicable grader ids
      └── expected_checks / metadata
  → Run pins
      ├── Agent Version
      ├── Adapter Version  → AdapterRegistry → concrete adapter
      ├── Prompt Version
      ├── Grader Version(s)
      ├── platform_version_id (free-text execution label)
      └── optional Suite Version
  → Worker
      → provision Docker sandbox
      → materialize repository @ SHA (verify HEAD)
      → inject pinned prompt
      → resolve adapter identity from pins (fail closed if unsupported)
      → execute adapter (live | deterministic)
      → capture events / artifacts
      → grade the SAME workspace (objective + optional judge)
      → persist structured Scores → complete / fail
  → Suite (optional)
      → fan-out one Run per composition CaseVersion
      → aggregate pass rate / average score from pinned Runs
```

## Canonical v1 coding agent

| Axis | Choice |
|------|--------|
| Coding agent | Gemini CLI (`gemini_cli`) |
| Adapter | `GeminiAdapter` |
| Why | Production live path with Docker e2e, workspace pytest, provider failure classification |
| Deterministic CI path | Synthetic Claude NDJSON (`claude_code`) for architecture verification only |
| Other adapters | Registered for **live** resolution; unsupported / misconfigured pins **fail the run** — never silently fall back |

## Step-by-step recipe

1. **Create a project**.
2. **Create a case** and draft a case version with public `repository_url`, exact `commit_sha`, optional `subdirectory`, and `applicable_grader_ids`.
3. **Create and publish a prompt version** with the exact agent instructions.
4. **Publish the case version** (pins the prompt + repo revision). Case versions are immutable after publication.
5. **Create an agent** and **adapter** named `gemini_cli` (or `claude_code` for deterministic CI).
6. **Publish agent + adapter versions**.
7. **Create and publish grader version(s)** declared on the case (objective and/or rubric).
8. **Launch a run** pinning published case / prompt / agent / adapter / graders (+ optional suite).
9. **Worker** claims the run from Redis.
10. **Sandbox** is provisioned (isolated Docker container).
11. **Repository materializer** clones/fetches, checks out `--detach <sha>`, verifies `HEAD`.
12. **Adapter identity** is resolved from the pinned Adapter Version name → registry key + credentials.
13. **Adapter** executes against the materialized workspace with the pinned prompt.
14. **Objective graders** evaluate events and/or the same workspace (e.g. `workspace:pytest …`).
15. **Rubric graders** invoke a configured judge provider (optional) and validate structured JSON.
16. **Scores** persist with a structured `detail` payload; provenance is queryable via API.
17. **Run detail / provenance** shows pins, repository, commit, adapter key, graders, scores, failure reasons.

## Suite execution

```
POST /v1/suites/{id}/versions/{version_id}/execute
GET  /v1/suites/{id}/versions/{version_id}/results
```

1. Validate every composition CaseVersion (pinnable, same project, exact SHA).
2. Resolve graders (explicit refs or each case’s applicable active versions).
3. Create + enqueue one EvaluationRun per case (independent execution).
4. Aggregate from Runs pinned to that SuiteVersion: totals, completed/failed/cancelled, pass rate, average score, per-case results.

Cancellation of individual runs does not invent suite state — aggregation always reflects current Run rows.

## Execution modes

| Mode | Env | Meaning |
|------|-----|---------|
| `deterministic` (default) | `WORKER_ADAPTER_MODE=deterministic` | Synthetic Claude NDJSON + writes `main.py`. CI / architecture verification only. |
| `live` | `WORKER_ADAPTER_MODE=live` | Real adapter CLI inside the sandbox. Requires provider credentials. **Fails fast** if credentials are missing. |

There is **no silent fallback** from live → deterministic or from an unsupported adapter → another vendor.

## Grading contract

Every Score `detail` normalizes toward:

| Field | Meaning |
|-------|---------|
| `grader` | Grader name |
| `family` | `objective` or `rubric` |
| `passed` | Boolean verdict when applicable |
| `score` / `max_score` | Numeric measurement |
| `reason` | Human-readable explanation |
| `evidence` | Supporting facts (exit codes, missing files, criteria, …) |
| `metadata` | Family-specific extras (judge model, fingerprint, …) |

### Objective graders

Built-in: test pass (incl. workspace pytest), exit code, expected file, diff, JSON output, lint, build.

### Judge / rubric graders

- Providers: `anthropic`, `openai`, `gemini`, `groq`, `mock`
- Configure with `JUDGE_PROVIDER` and the matching API key
- Auto-detect from available keys when `JUDGE_PROVIDER` is unset
- Disable with `JUDGE_PROVIDER=none`
- Judge output must be structured JSON (`passed`/`score`/`numeric` + non-empty `reason`; optional `criteria`)
- Malformed judge output → explicit grader failure (never silent skip)
- Rubric pin with no judge → actionable fail-closed error

### Score aggregation policy

- Individual objective and rubric scores remain separately visible
- Overall numeric average only when every produced score has a numeric value
- **Objective `passed=false` is a hard failure** — an LLM judge cannot override a pytest/build/lint failure
- Run passes only when every score reports `passed=true`

## Credentials

| Variable | Used for |
|----------|----------|
| `GEMINI_API_KEY` | Live Gemini CLI (primary coding agent) |
| `GOOGLE_API_KEY` | Alternate env name accepted by Gemini CLI |
| `ANTHROPIC_API_KEY` | Live Claude Code + optional rubric judge |
| `OPENAI_API_KEY` | Optional OpenAI judge |
| `GROQ_API_KEY` | Optional Groq judge (`llama-3.3-70b-versatile` default; `GROQ_MODEL` override). `GRAQ_API_KEY` accepted only as a misspelled alias. |
| `JUDGE_PROVIDER` | `groq` \| `anthropic` \| `openai` \| `gemini` \| `mock` \| `none` |

Credentials are injected via worker env → sandbox allowlist only. Never stored in Postgres, Redis, API responses, events, or Git.

## Provider failure semantics (Gemini)

| Condition | Expected outcome |
|-----------|------------------|
| Missing `GEMINI_API_KEY` in live mode | Fail fast at adapter resolution |
| Invalid API key | Adapter failure (`Gemini authentication failed`) |
| Quota / rate limit (HTTP 429) | Adapter failure (`Gemini API rate limit exceeded`) — not a successful evaluation |
| CLI non-zero / result error | Actionable `Gemini CLI failed: …` |
| Agent completes without fixing tests | Run may complete; workspace grader `passed=false` |

## Workspace grading

Pin a grader with specification:

```
workspace:python3 -m pytest tests/ -q
```

The worker runs that command inside the **same materialized workspace** the agent modified.

## Reproducibility / provenance

`GET /v1/runs/{run_id}/provenance` answers “what exactly happened?”:

- case / prompt / agent / adapter / grader version pins
- repository URL + exact commit SHA + subdirectory
- adapter name / registry key / version label
- platform_version_id
- score aggregate + partial grading flags
- failure / cancellation reasons

Secrets are never included.

## Supported adapters (registry)

| Key | Deterministic | Live |
|-----|---------------|------|
| `claude_code` | Yes (canonical synthetic) | Yes (`ANTHROPIC_API_KEY`) |
| `gemini_cli` | No (fail closed) | Yes (`GEMINI_API_KEY` / `GOOGLE_API_KEY`) |
| `cursor` | No | Yes |
| `codex` | No | Yes |
| `aider` | No | Yes |

## Live verification commands

```bash
cp .env.example .env
# set GEMINI_API_KEY=... locally (never commit)

docker build -f infrastructure/docker/Dockerfile.sandbox \
  --build-arg EVALFORGE_INSTALL_GEMINI_CLI=1 \
  -t evalforge/sandbox:local .

uv run pytest adapters/tests workers/tests graders/tests application/tests \
  -m "not integration and not gemini_live"

EVALFORGE_LIVE_GEMINI_DOCKER=1 \
  uv run pytest workers/tests/test_gemini_live_integration.py -m gemini_live -v
```

After runs, verify cleanup:

```bash
docker ps -a --filter "label=evalforge.component=sandbox"
```

## Known limitations

- `platform_version_id` remains free-text (no catalog UI)
- Execution mode is worker-scoped (not a Run column); provenance surfaces adapter identity + pins
- Private git authentication is out of scope
- Live Gemini verification requires a real API key and may be quota-blocked (honest provider failure, not harness success)
- Judges are optional; objective-only evaluations never require Groq/Anthropic/OpenAI judge keys

## Related

- [phase-6-evaluation-engine-plan.md](./phase-6-evaluation-engine-plan.md) — Phase 6 audit / extension points
- [phase-4-execution-contract-audit.md](./phase-4-execution-contract-audit.md)
- [grader-architecture.md](./grader-architecture.md)
- [execution-engine-architecture.md](./execution-engine-architecture.md)
- Canonical repo source: `evaluations/canonical/calculator-fix/`
