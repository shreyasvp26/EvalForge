# Phase 14 — verification

**Branch:** `feat/phase-14-real-product-loop`  
**Base:** `feat/phase-13-byok-model-configuration` (`795360e`)

## Automated tests (this machine)

| Suite | Result |
|-------|--------|
| Domain publication | pass |
| Application GitHub publication (fakes) | pass |
| Worker BYOK inject | pass |
| Worker lifecycle / orchestration | pass |
| API GitHub + runs + DI | pass |
| Web settings nav | pass |
| Docker worker e2e (`EVALFORGE_LIVE_WORKER_DOCKER=1`) | **pass** — real Docker sandbox, SHA materialization, grade, complete |

## Live provider verification

| Check | Status |
|-------|--------|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | **not set** — live Gemini run **BLOCKED** (credentials), not an implementation failure |
| OmniRoute live | **not verified** (optional; out of mandatory path) |

## GitHub live verification

| Check | Status |
|-------|--------|
| Unit/integration with `FakeGitHubPullRequestPublisher` | pass |
| Live GitHub branch/PR against a real repo | **not performed** |

## Known limitations

- GitHub login OAuth remains identity-only (`read:user user:email`). Publication uses a separate encrypted PAT/token (Settings → GitHub).
- Private-repo clone during sandbox materialization still uses public git fetch; PAT is used for Git Data/PR APIs, not injected into the agent sandbox.
- API `POST /v1/runs/{id}/publish` without captured workspace changes is idempotent lookup / ineligible publication — worker auto-publish is the path that has live file contents.
- Sequential multi-task checkpoints are not implemented.

## Docker

Daemon available. Image `evalforge/sandbox:local` present. Production Docker integration test passed.
