# Phase 14 — Real Product Execution Loop Audit

**Branch:** `feat/phase-14-real-product-loop`  
**Base:** `feat/phase-13-byok-model-configuration` @ `795360e` (Phase 12 is on `main`; Phase 14 stacks on Phase 13 BYOK)  
**Principle:** Complete the existing product loop. Do not redesign Agent / Adapter / Model / Provider / Credential / Gateway / Sandbox / Grader.

## Locked product question

Can a user give EvalForge a real engineering task against their GitHub repository, choose agent/model with BYOK, run safely in Docker, grade the result, and receive a reviewable PR on PASS?

## What already exists (reuse)

| Capability | Location | Verdict |
|------------|----------|---------|
| Case = engineering task | `domain/.../evaluation_management/case.py` | **Reuse as Task** — no new aggregate |
| CaseVersion pins repo SHA + graders + prompt | same | Sufficient for Task semantics |
| CreateRun + pins + runtime_request | `application/.../use_cases/run.py` | Exists (Phase 12/13) |
| BYOK provider connections + Fernet | `infrastructure/.../auth/provider_connection.py` | Exists; worker inject incomplete |
| Exact Gemini `--model` pinning | `adapters/.../gemini/adapter.py` | Exists |
| Docker sandbox + SHA materialization | `workers/.../repository_materializer.py` | Exists |
| Deterministic graders | `graders/` | Exists |
| Score aggregation / PASS policy | `application/.../scoring/aggregation.py` | Exists |
| Provenance (provider/model/credential ref) | `application/.../use_cases/provenance.py` | Exists; missing publication fields |
| SSE / run status | Redis fanout + web polling | Exists through grading terminal |
| Suite / benchmark independence | `CreateSuiteRuns` | Preserve; not required for single-task UX |
| GitHub OAuth (login only) | `GitHubOAuthProvider` scopes `read:user user:email` | **Insufficient for PR** |

## Gaps (must build)

1. **GitHub publication on PASS** — no ports, no branch/commit/push/PR path.
2. **Publication vs evaluation separation** — no `publication` state on Run; only eval `failure_category`.
3. **Idempotent publish retry** — not present.
4. **Sandbox destroyed immediately on `GRADING_FINISHED`** — workspace gone before publish; must capture diff/files or publish before destroy.
5. **BYOK secret → sandbox env** — provenance records `user:…:conn:…` but sandbox still uses host allowlist only.
6. **Task-first UX** — domain OK; UI still says “Cases”; no PR link / publication panel on run detail.
7. **GitHub repo authorization** — OAuth tokens not stored; no `repo` / `public_repo` scope.

## Design decisions

| Decision | Choice |
|----------|--------|
| Task entity | Keep `EvaluationCase`; product language “Task” in UI/docs |
| Publication storage | `runs.publication` JSONB (status, branch, commit, PR URL, error) — **not** a RunStatus |
| Eval FAIL | `publication.status = skipped`; never create branch/PR |
| Publish FAIL after PASS | Run stays `completed` + scores intact; `publication.status = failed` |
| GitHub credentials | User-scoped encrypted GitHub connection (OAuth repo authorize and/or PAT), Fernet reuse — **not** a second secret architecture |
| Token in sandbox | **Never** for agent execution; publication uses GitHub API from worker with files read from sandbox |
| Branch naming | `evalforge/task-<case_id>-run-<run_id>` |
| OmniRoute | Remain optional; no live claim in this phase |
| Sequential multi-task | Out of scope |

## Implementation order

1. Audit (this doc)
2. Task/run product semantics (terminology + eligibility helpers)
3. BYOK runtime inject + workspace capture before destroy
4. Publication domain + ports + GitHub infra
5. Publish-on-PASS orchestration (idempotent)
6. API + web loop surfaces
7. Tests + docs + verification report

## Verification honesty

| Check | Status at audit start |
|-------|----------------------|
| Docker daemon | Available |
| `evalforge/sandbox:local` image | Present |
| Live Gemini | Not yet re-run; prior Phase 5/11 proofs exist; quota may block |
| Live GitHub PR | Not verified until implemented + exercised |
| OmniRoute live | Not in scope for mandatory path |
