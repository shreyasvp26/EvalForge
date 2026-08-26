# Phase 9 — Multi-Agent Adapter Foundations Audit

**Branch:** `feat/phase-9-multi-agent-evaluation`  
**Base:** `main` @ Phase 7 (`a4857b2`)  
**Note:** Phase 8 PRs [#22](https://github.com/shreyasvp26/EvalForge/pull/22) (benchmark integrity) and [#23](https://github.com/shreyasvp26/EvalForge/pull/23) (OAuth) were still open when Phase 9 started. This audit reflects **main**, not unmerged Phase 8 heads.

## A. Verified support matrix (actual, not aspirational)

| Adapter key   | Deterministic | Live factory | Production status                         |
|---------------|---------------|--------------|-------------------------------------------|
| `gemini_cli`  | no (fail closed) | yes       | **LIVE VERIFIED** (Docker e2e; may be provider-blocked by quota) |
| `claude_code` | synthetic NDJSON | yes     | **SYNTHETIC VERIFIED** (CI). Live wired, **not** Gemini-equivalent e2e gate |
| `cursor`      | no            | yes          | **REGISTERED / UNVERIFIED** — no CLI image install, allowlist gap |
| `codex`       | no            | yes          | **REGISTERED / UNVERIFIED** — no CLI image install, allowlist gap |
| `aider`       | no            | yes          | **REGISTERED / UNVERIFIED** — no CLI image install, allowlist gap |
| unknown       | —             | —            | **FAIL CLOSED** (`AdapterResolutionError`) |

## B. Resolution path

```
CreateRun → pins.adapter_version_id
  → Worker PinnedAdapterResolver.resolve_factory(run_id)
    → Adapter.name / version.label → normalize_adapter_key()
    → WORKER_ADAPTER_MODE → deterministic | live
    → AdapterRegistry.resolve(key, mode)
      → live: _require_live_credentials(key) then factory
      → deterministic: only if factory registered (Claude only)
  → SdkAdapterBridge → DockerSandbox → graders
```

Key files:

- `workers/.../integration/adapter_registry.py` — registry + pin resolver
- `workers/.../integration/process.py` — composition
- `workers/.../integration/adapter_bridge.py` — SDK bridge
- `workers/.../integration/sandbox_adapter.py` — env allowlist
- `adapters/src/agent_eval_adapters/{gemini,claude_code,cursor,codex,aider}/`

## C. Hardcoded / soft-fallback risks

| Risk | Location | Severity |
|------|----------|----------|
| `select_adapter_factory(live)` returns Claude | `process.py` | Medium — legacy helper |
| `fallback_factory = adapter_factory or default_claude_factory()` | `process.py` | High if resolver bypassed |
| Soft prompt `"solve the case"` | `prompt_resolver.py` | Medium |
| Sandbox `auto` → FakeDockerEngine | `process.py` | Medium (logged) |
| Fuzzy substring matching in `normalize_adapter_key` | registry | Low–medium |
| Cursor/Codex/Aider registered live without Docker e2e | registry | **Overstates support** |

## D. Credential handling

Default allowlist: `ANTHROPIC_API_KEY,GEMINI_API_KEY,GOOGLE_API_KEY,PATH,HOME,TERM`

Gaps vs live credential policy:

- `CURSOR_API_KEY` — required by policy, **not** in default allowlist
- `OPENAI_API_KEY` — required for Codex/Aider, **not** in default allowlist

Secrets must never enter Run metadata, provenance, events, artifacts, or logs.

## E. Comparability gaps on main

- `execution_mode` is worker-scoped (`WORKER_ADAPTER_MODE`); provenance often lacks a durable mode snapshot on main
- Adapter identity derived from free-text `Adapter.name` (no durable `adapter_key` column)
- No authoritative capability descriptor (required credentials, verified modes, CLI requirements)

## F. Phase 9 smallest production-grade path

1. **Capability registry** — explicit support status per adapter (`verified_live`, `synthetic_only`, `registered_unverified`, `unsupported`)
2. **Fail closed** — live resolve only for verified adapters unless an explicit operator override is set
3. **Remove Claude soft fallback** when pin resolver is active; fail closed if resolution is missing
4. **Align allowlists** with credential policy for adapters that remain eligible
5. **Persist `adapter_key` + `execution_mode`** on run/provenance for comparability
6. **Benchmark matrix** — extend comparison/reporting without a second benchmark system
7. **Live-verify additional adapters only with real Docker proof**; otherwise leave unsupported
8. **Preserve Gemini** — regression path; honest provider-blocked if quota exhausted

## G. Engineering principle

Do not optimize for number of dropdown options. Optimize for trustworthy evaluation:

> When EvalForge says Agent A scored 8.2 and Agent B scored 7.6, both agents actually ran against the same immutable benchmark.

One genuinely verified adapter is more valuable than five fake integrations.
