# How EvalForge evaluates a coding agent

This is the Phase 4 **canonical evaluation path**: a reproducible,
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
      → run pinned objective graders
      → persist scores → complete / fail
```

## Canonical v1 agent

| Axis | Choice |
|------|--------|
| Coding agent | Claude Code (`claude_code`) |
| Adapter | `ClaudeCodeAdapter` |
| Why | Only adapter with production worker wiring, deterministic inject path, and Docker e2e coverage |
| Other adapters | Registered for **live** resolution (`cursor`, `codex`, `gemini_cli`, `aider`); unsupported / misconfigured pins **fail the run** — never silently fall back to Claude |

## Step-by-step recipe

1. **Create a project** (API or UI).
2. **Create a case** and draft a case version with:
   - `repository_url` (public HTTPS for v1)
   - exact `commit_sha`
   - optional `subdirectory`
   - `applicable_grader_ids`
3. **Create and publish a prompt version** with the exact agent instructions.
4. **Publish the case version** (pins the prompt + repo revision).
5. **Create an agent** and **adapter** named `claude_code` (name drives registry resolution).
6. **Publish agent + adapter versions**.
7. **Create and publish objective grader version(s)** declared on the case.
8. **Launch a run** pinning published case / prompt / agent / adapter / graders.
9. **Worker** claims the run from Redis.
10. **Sandbox** is provisioned (isolated Docker container).
11. **Repository materializer** clones/fetches, checks out `--detach <sha>`, verifies `HEAD`.
12. **Adapter** executes against the materialized workspace with the pinned prompt.
13. **Graders** evaluate events and (for ExpectedFile) confirm files exist in that workspace.
14. **Run detail** shows pins, repository, commit, adapter, prompt, scores, and failure reasons.

## Execution modes

| Mode | Env | Meaning |
|------|-----|---------|
| `deterministic` (default) | `WORKER_ADAPTER_MODE=deterministic` | Synthetic Claude NDJSON + writes `main.py` into the workspace. For CI / local architecture verification only. |
| `live` | `WORKER_ADAPTER_MODE=live` | Real adapter CLI inside the sandbox. Requires provider credentials (e.g. `ANTHROPIC_API_KEY` for Claude). **Fails fast** if credentials are missing — never pretends a live agent ran. |

There is **no silent fallback** from live → deterministic or from an unsupported adapter → Claude.

## Docker requirements

- Docker Desktop (or daemon) running
- Compose stack: `infrastructure/docker/docker-compose.yml`
- Sandbox image `evalforge/sandbox:local` (includes `git`)
- For repository materialization: sandbox network must allow egress
  (`WORKER_SANDBOX_NETWORK=bridge` or equivalent). `none` blocks `git fetch`.

## Credentials

- Live Claude: `ANTHROPIC_API_KEY` (injected into the worker / sandbox allowlist — never stored in Postgres, never shown in the UI, never logged)
- Private repositories: **not supported in v1** — use public HTTPS repos. Do not embed tokens in `repository_url`.

## Supported adapters (registry)

| Key | Deterministic | Live |
|-----|---------------|------|
| `claude_code` | Yes (canonical) | Yes (needs `ANTHROPIC_API_KEY`) |
| `cursor` | No | Yes (needs Cursor / Anthropic credentials) |
| `codex` | No | Yes (needs `OPENAI_API_KEY`) |
| `gemini_cli` | No | Yes (provider credentials) |
| `aider` | No | Yes (provider credentials) |

## Known limitations

- `platform_version_id` remains free-text (no catalog product yet)
- Execution mode is **worker-scoped**, not stored on the Run row (UI surfaces that)
- Objective graders consume execution events; ExpectedFile paths are additionally probed on disk while the sandbox still exists
- Rubric graders require a configured judge; pins without a judge **fail closed**
- Private git authentication is out of scope for Phase 4
- Live coding-agent verification requires real credentials; without them, only deterministic + fail-closed live config are verified

## Related

- [phase-4-execution-contract-audit.md](./phase-4-execution-contract-audit.md) — pre-implementation audit
- [execution-engine-architecture.md](./execution-engine-architecture.md) — orchestration ports
