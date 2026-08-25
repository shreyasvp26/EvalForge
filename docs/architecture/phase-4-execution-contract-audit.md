# Phase 4 — Evaluation Execution Contract Audit

**Branch:** `feat/phase-4-real-evaluation`  
**Base:** `main` @ `335ae17`  
**Date:** 2026-08-25  
**Status:** Audit complete; implementation follows this document.

---

## 1. Current run contract (actual behavior on main)

```
UI / API CreateRun
  → RunFactory validates pins (project, pinnable versions, grader ⊆ case declarations)
  → Persist EvaluationRun (queued) + enqueue Redis
  → Worker claims
  → ManagedSandboxAdapter.provision  (empty /workspace, no mounts)
  → SdkAdapterBridge
       prompt = hardcoded "solve the case"
       adapter = ClaudeCodeAdapter ALWAYS
                  (WORKER_ADAPTER_MODE=deterministic by default → injected NDJSON)
  → Events / artifacts persisted
  → PinBasedGraderResolver → objective ExpectedFile|Diff only; rubrics skipped
  → Scores (detail written to DB, not exposed on DTO/API on main)
  → Complete / fail / cancel
```

**Pins stored on Run:** `project_id`, `case_version_id`, `prompt_version_id`,
`agent_version_id`, `adapter_version_id`, `platform_version_id`,
`grader_version_ids[]`, optional `suite_version_id`.

**Case Version stores but worker ignores:** `repository_url`, `commit_sha`,
`subdirectory`, `expected_checks`.

**Agent / Adapter versions store:** label + notes only — **no** `adapter_type`,
provider, model, or credential reference.

---

## 2. What is already correct

- Domain pin model and `RunFactory` invariants (drafts, cross-project, grader declarations)
- Run status machine: `created → queued → running → grading → completed|failed|cancelled`
- Worker orchestration ports (sandbox / adapter / events / grading / status)
- Docker sandbox isolation defaults (network, env allowlist)
- Adapter SDK shared by Claude / Cursor / Codex / Gemini / Aider
- Claude adapter integrated in production worker with deterministic + live CLI modes
- Objective graders implemented; score write path includes `detail`
- Architecture docs already require **repository preparation** and **prompt delivery**
  (`docs/architecture/execution-engine-architecture.md`)

---

## 3. What is currently hardcoded

| Concern | Hardcoded value | Location |
|---------|-----------------|----------|
| Prompt | `"solve the case"` | `SdkAdapterBridge.prompt` |
| Adapter | Claude only | `select_adapter_factory` / `default_claude_factory` |
| Working directory | `/workspace` | `SdkAdapterBridge` |
| Default mode | `WORKER_ADAPTER_MODE=deterministic` | `process.py` |
| Expected file default | `main.py` | `grader_resolver._parse_expected_paths` |
| Platform (UI) | `"platform-1.0.0"` free-text | `create-run-page.tsx` |
| Sandbox mounts | empty `()` | `ManagedSandboxAdapter.default_sandbox_spec` |

**Critical finding:** Agent/adapter pins are **bookkeeping IDs**. Runtime never
resolves `adapter_version_id` → concrete adapter. There is **no silent
Claude fallback from another pin** — Claude is simply the only factory wired.

---

## 4. What is missing

1. Resolve pinned **Prompt Version content** into the adapter
2. **Adapter registry** keyed by adapter identity (no silent Claude when another
   adapter is pinned)
3. **Repository materialization** at exact `commit_sha` before agent start
4. Verify HEAD == requested SHA
5. Grade against the **same** materialized workspace the agent modified
6. Explicit **live vs deterministic** modes (fail fast when live lacks credentials)
7. Rubric pins: fail clearly or wire judge — do not silent-skip when required
8. Expose score `detail` / reason on API + UI (persist already works on main)
9. Runtime metadata for inspectability (derive from pins + case where possible)
10. Private-repo credential injection (public repos OK for canonical v1)

**Unmerged Phase 3 branch** (`feat/phase-3-run-experience`) already implements
items 1, partial 5 (grader mapping), 8, and launch UX hardening. Phase 4 will
absorb those commits, then add registry + materialization.

---

## 5. What Phase 4 must implement

Target contract:

```
Project → Case Version
  ├── Prompt Version (content)
  ├── repository_url + exact commit_sha (+ subdirectory)
  └── applicable graders
        ↓
Run pins AgentVersion + AdapterVersion + Prompt + Graders + platform
        ↓
Worker
  → resolve AdapterVersion → AdapterRegistry → concrete adapter
  → provision sandbox
  → materialize repo @ SHA (verify HEAD)
  → inject pinned prompt
  → execute adapter (live|deterministic explicit)
  → capture events/artifacts
  → resolve + run pinned graders on same workspace
  → persist scores (with detail)
  → complete / fail with clear reasons
```

### Canonical v1 evaluation

| Axis | Choice | Why |
|------|--------|-----|
| Coding agent | Claude Code | Sole adapter wired in worker; deterministic inject path; Docker e2e; CLI install flag |
| Adapter | `ClaudeCodeAdapter` | Best tests + production composition surface |
| Model/provider | Whatever Claude CLI uses (`ANTHROPIC_API_KEY`) | No separate model pin in domain yet |
| Repo | Public `repository_url` | Private git auth deferred if not already present |
| Revision | Exact `commit_sha` | Architecture requirement |
| Prompt | Pinned Prompt Version content | Architecture requirement |
| Grader | Published objective grader pin(s) | Rubric needs judge — fail clearly if pinned without judge |
| Sandbox | Isolated Docker | Phase 2 complete |
| Execution mode | `live` when configured; `deterministic` **only** when explicitly set | No silent fallback |

Other adapters (Cursor, Codex, Gemini, Aider) remain SDK-ready libraries.
Register them only when resolution + tests are real; unsupported pins **fail
the run** with a clear message.

---

## 6. Explicitly out of scope

- Frontend redesign / SSE / analytics / billing / marketplace / SSO
- Architecture rewrite (FastAPI / Next / Postgres / Redis / Docker stay)
- Platform version catalog product (document free-text limitation; keep pin explicit)
- Using `expected_checks` as a grader scheduler
- Agent credential vault UX
- Fake adapters registered to look complete
- Evaluating against a branch name instead of a commit SHA

---

## 7. Implementation order

1. Absorb Phase 3 execution plumbing (prompt resolve, grader map, score detail, launch validation)
2. Adapter registry from AdapterVersion identity — fail closed
3. Explicit live vs deterministic mode semantics
4. Repository materializer (clone/fetch → checkout SHA → verify HEAD)
5. Orchestration: materialize after provision, before adapter
6. Grading against materialized workspace
7. Failure-path tests + deterministic E2E
8. Docker verification
9. Live-agent verification if credentials available, else document NOT VERIFIED
10. Docs: “How EvalForge evaluates a coding agent”

---

## 8. Key files

| Concern | Path |
|---------|------|
| Case + reference repo | `domain/.../evaluation_management/case.py` |
| Run pins / factory | `domain/.../execution/run.py`, `run_factory.py` |
| Agent / Adapter | `domain/.../agent_integration/{agent,adapter}.py` |
| Worker composition | `workers/.../integration/process.py` |
| Adapter bridge | `workers/.../integration/adapter_bridge.py` |
| Grader resolver | `workers/.../integration/grader_resolver.py` |
| Sandbox adapter | `workers/.../integration/sandbox_adapter.py` |
| Orchestrator | `workers/.../lifecycle/orchestrator.py` |
| Claude adapter | `adapters/.../claude_code/adapter.py` |
| Mounts helper | `sandbox/.../docker/mounts.py` |
| Architecture intent | `docs/architecture/execution-engine-architecture.md` |
