# How EvalForge evaluates a coding agent

This is the Phase 5 **canonical evaluation path**: a reproducible,
inspectable coding-agent evaluation from Case pins through sandbox execution
to graded scores.

## Target contract

```
Project
  → Case Version
      ├── Prompt Version (exact content)
      ├── repository_url + exact commit_sha
      └── applicable grader ids
  → Run pins
      ├── Agent Version
      ├── Adapter Version  → AdapterRegistry → concrete adapter
      ├── Prompt Version
      ├── Grader Version(s)
      └── platform_version_id (free-text today)
  → Worker
      → provision Docker sandbox
      → materialize repository @ SHA (verify HEAD)
      → inject pinned prompt
      → execute resolved adapter (live | deterministic)
      → capture events / artifacts
      → probe ExpectedFile paths in the same workspace
      → run workspace pytest for `workspace:` test grader pins
      → run pinned objective graders
      → persist scores → complete / fail
```

## Canonical v1 agent (Phase 5)

| Axis | Choice |
|------|--------|
| Coding agent | **Gemini CLI** (`gemini_cli`) |
| Adapter | `GeminiAdapter` — runs `gemini --output-format stream-json` inside the sandbox |
| Execution | Live only (`WORKER_ADAPTER_MODE=live`) |
| Repository | Public `shreyasvp26/evalforge-calculator-fix` at exact commit SHA |
| Prompt | Pinned prompt version (fix `calculator.add`) |
| Grader | Objective `TestPassGrader` with `workspace:python3 -m pytest tests/ -q` |
| Credential | `GEMINI_API_KEY` (never committed, never in UI) |

Claude Code remains the canonical **deterministic** path for CI (`WORKER_ADAPTER_MODE=deterministic`).

Other adapters (`cursor`, `codex`, `aider`) are registered for live resolution; unsupported or misconfigured pins **fail the run** — never silently fall back to Claude or Gemini.

## Step-by-step recipe (live Gemini)

1. **Configure credentials** — set `GEMINI_API_KEY` in your local `.env` (see below).
2. **Build sandbox image with Gemini CLI**:
   ```bash
   EVALFORGE_INSTALL_GEMINI_CLI=1 docker compose -f infrastructure/docker/docker-compose.yml build sandbox-image
   ```
3. **Start the stack** (workers need Docker socket + bridge network for git fetch and Gemini egress):
   ```bash
   WORKER_ADAPTER_MODE=live \
   WORKER_SANDBOX_NETWORK=bridge \
   docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up --build
   ```
4. **Create a project** (API or UI).
5. **Create a case** with:
   - `repository_url`: `https://github.com/shreyasvp26/evalforge-calculator-fix.git`
   - `commit_sha`: pinned broken implementation SHA (see `workers/.../canonical_evaluation.py`)
   - prompt: fix `calculator.add` so `add(2, 3) == 5`
   - grader specification: `workspace:python3 -m pytest tests/ -q`
6. **Create agent + adapter** named `gemini_cli`.
7. **Launch a run** with `WORKER_ADAPTER_MODE=live`.
8. **Inspect run detail** — pins, repository, commit, adapter, prompt, scores, events, failure reason.

## Execution modes

| Mode | Env | Meaning |
|------|-----|---------|
| `deterministic` (default) | `WORKER_ADAPTER_MODE=deterministic` | Synthetic Claude NDJSON + writes `main.py`. CI / architecture verification only. |
| `live` | `WORKER_ADAPTER_MODE=live` | Real adapter CLI inside the sandbox. Requires provider credentials. **Fails fast** if credentials are missing. |

There is **no silent fallback** from live → deterministic or from an unsupported adapter → another vendor.

## Docker requirements

- Docker Desktop (or daemon) running
- Compose stack: `infrastructure/docker/docker-compose.yml`
- Sandbox image `evalforge/sandbox:local` with `EVALFORGE_INSTALL_GEMINI_CLI=1` for Gemini
- `WORKER_SANDBOX_NETWORK=bridge` for repository fetch and live Gemini CLI egress
- `WORKER_SANDBOX_ENV_ALLOWLIST` must include `GEMINI_API_KEY` (and optionally `GOOGLE_API_KEY`)

## Credentials

| Variable | Used for |
|----------|----------|
| `GEMINI_API_KEY` | Live Gemini CLI inside sandbox (primary) |
| `GOOGLE_API_KEY` | Alternate env name accepted by Gemini CLI |
| `ANTHROPIC_API_KEY` | Live Claude Code + optional rubric judge |

Credentials are injected via worker env → sandbox allowlist only. Never stored in Postgres, Redis, or API responses.

## Workspace grading

Objective graders normally consume execution events. For reproducible proof that the agent fixed the repository, pin a grader with specification:

```
workspace:python3 -m pytest tests/ -q
```

The worker runs that command inside the **same materialized workspace** the agent modified, then `TestPassGrader` scores the exit code. This is not a second clone and not the host working tree.

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
# Unit + integration (no live Gemini)
uv run pytest workers/tests -m "not integration"

# Live Docker (deterministic Claude + git materialization)
EVALFORGE_LIVE_WORKER_DOCKER=1 uv run pytest workers/tests/test_docker_production_integration.py -m integration

# Live Gemini Docker proof (requires GEMINI_API_KEY + Gemini CLI in sandbox image)
EVALFORGE_INSTALL_GEMINI_CLI=1 docker compose -f infrastructure/docker/docker-compose.yml build sandbox-image
EVALFORGE_LIVE_GEMINI_DOCKER=1 GEMINI_API_KEY=... uv run pytest workers/tests/test_gemini_live_integration.py -m gemini_live
```

After a live run, verify cleanup:

```bash
docker ps -a | grep run-
```

No EvalForge sandbox containers should remain for completed runs.

## Known limitations

- Gemini has no deterministic inject path — `WORKER_ADAPTER_MODE=deterministic` with a Gemini pin fails closed
- Live Gemini verification requires a real API key and network egress from the sandbox
- `platform_version_id` remains free-text
- Execution mode is worker-scoped, not stored on the Run row
- Rubric graders require a configured judge; pins without a judge fail closed
- Private git authentication is out of scope

## Related

- [phase-4-execution-contract-audit.md](./phase-4-execution-contract-audit.md)
- [execution-engine-architecture.md](./execution-engine-architecture.md)
- Canonical repo source: `evaluations/canonical/calculator-fix/`
