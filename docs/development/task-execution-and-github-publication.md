# Task execution and GitHub publication

Phase 14 completes the single-task product loop:

Project → Task (Case) → Agent → Model → BYOK → Docker sandbox → grade →
PASS → GitHub branch → commit → Pull Request

## Task semantics

`EvaluationCase` remains the domain aggregate. Product language uses **Task**.
A published Case Version pins:

- natural-language instructions (Prompt Version)
- repository URL + exact commit SHA (+ optional subdirectory)
- expected checks / grader declarations

Suites remain optional for benchmarks; single-task runs do not require them.

## Run configuration

CreateRun records non-secret `runtime_request`:

- provider / model / gateway / routing
- `provider_connection_id` / `credential_ref_id`
- `requested_by_actor_id`
- optional `github_connection_id`
- `auto_publish_on_pass` (`1`/`0`)

## BYOK

User provider connections stay Fernet-encrypted. The worker resolves
`user:…:conn:…` refs and injects secrets only into the sandbox environment under
known provider env vars. Secrets never appear in provenance, events, or APIs.

## GitHub publication

Publication is **separate** from evaluation `RunStatus`:

| Evaluation                               | Publication                                       |
| ---------------------------------------- | ------------------------------------------------- |
| `completed` + scores pass                | may publish                                       |
| `completed` + scores fail                | `publication.status=skipped` — no branch/PR       |
| `completed` + scores pass + GitHub fails | evaluation unchanged; `publication.status=failed` |

Branch naming: `evalforge/task-<case_id>-run-<run_id>`

Idempotency: existing PR for that branch is reused; no force-push; never modifies main.

Connect a token under **Settings → GitHub** (encrypted PAT). Login OAuth scopes
remain `read:user user:email`; publication uses the separate stored credential.

Worker auto-publish runs after CompleteRun while the sandbox is still alive
(`EVALFORGE_AUTO_PUBLISH_ON_PASS=1` by default). API retry:
`POST /v1/runs/{id}/publish`.

## Verification honesty

- Docker: available when the host daemon and `evalforge/sandbox:local` exist.
- Live Gemini: requires BYOK / env credentials; quota may block.
- Live GitHub PR: requires a real token + writable repository; unit tests use fakes.

## Related

- [Phase 14 audit](../architecture/phase-14-real-product-loop-audit.md)
- [BYOK provider connections](../architecture/byok-provider-connections.md)
