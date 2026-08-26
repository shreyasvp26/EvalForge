# Adapter Support Matrix (Phase 9)

EvalForge marks an adapter **VERIFIED** only after real Docker end-to-end
execution proof. Recognition of an adapter key is not production support.

## Authoritative matrix

| Adapter key   | Deterministic | Live | Status | Evidence |
|---------------|---------------|------|--------|----------|
| `gemini_cli`  | no            | yes  | **VERIFIED LIVE** | Docker e2e (`EVALFORGE_LIVE_GEMINI_DOCKER=1`); may be provider-blocked by quota |
| `claude_code` | synthetic     | no   | **SYNTHETIC ONLY** | CI deterministic NDJSON path |
| `cursor`      | no            | no   | **UNSUPPORTED** | SDK present; not registered |
| `codex`       | no            | no   | **UNSUPPORTED** | SDK present; not registered |
| `aider`       | no            | no   | **UNSUPPORTED** | SDK present; not registered |

API: `GET /v1/adapters/capabilities`

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `verified_live` | Live Docker e2e observed against a real coding-agent CLI |
| `synthetic_only` | Deterministic CI path — not a live coding agent |
| `implemented_unverified` | Wiring exists; live proof missing |
| `unsupported` | Not available for production evaluation |

## Fail-closed resolution

- Unknown pins → `adapter_unsupported`
- Unsupported keys (cursor/codex/aider/claude live) → `adapter_unsupported`
- Missing credentials for verified live adapters → `adapter_failure` with actionable reason
- No silent fallback from one adapter to another
- No silent live → deterministic fallback

## Credentials (never logged / never in provenance)

| Adapter | Required | Optional |
|---------|----------|----------|
| `gemini_cli` | `GEMINI_API_KEY` | `GOOGLE_API_KEY` |
| `claude_code` (synthetic) | — | `ANTHROPIC_API_KEY` (unused for synthetic) |

Default sandbox allowlist remains:
`ANTHROPIC_API_KEY,GEMINI_API_KEY,GOOGLE_API_KEY,PATH,HOME,TERM`

Do not expand the allowlist for unsupported adapters.

## Benchmark matrix

`POST /v1/runs/benchmark-matrix` with `{ "run_ids": [...] }` returns an
adapter × score matrix **only when** runs share the immutable benchmark
definition (case SHA, prompt, graders, platform, repository).

Incomparable runs return `comparable: false` with explicit mismatches.
Deterministic/synthetic cells are labeled via `execution_mode` and warned in notes.

## Adding a verified adapter (checklist)

1. Capability entry with required credentials / CLI install flag
2. Sandbox image installs the real CLI
3. Register live factory in `default_adapter_registry`
4. Fail-fast missing credential tests
5. Live Docker e2e against exact repository SHA
6. Workspace grading on the same sandbox
7. Cleanup: zero orphan EvalForge sandbox containers
8. Update this matrix only after observed success

Until step 8 succeeds, leave the adapter **UNSUPPORTED**.
