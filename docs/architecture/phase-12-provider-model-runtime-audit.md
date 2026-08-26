# Phase 12 — Provider & Model Runtime Audit

**Branch:** `feat/phase-12-provider-model-runtime`  
**Base:** `main` @ Phase 11 merge (`7b9fd51`)  
**Source of truth:** current repository code (not older phase reports alone)

## Executive summary

EvalForge already has strong **Agent / Adapter / Platform** versioning, **execution_mode** persistence, an **adapter capability registry**, secret-safe **provenance**, and **benchmark comparability**. It does **not** yet have first-class **provider / model / gateway / routing** identity for coding-agent execution.

Judge providers (`graders/.../providers/`) are a **separate plane** (rubric LLM-as-judge). They must not be conflated with coding-agent model/provider runtime.

**Design principle for Phase 12:** extend existing execution configuration + capability catalog + provenance/comparison. Do **not** invent parallel `Provider` / `ModelVersion` aggregates or a credential marketplace.

---

## Conceptual answers (required)

### What is an Agent?

Product-facing coding agent identity (e.g. “Gemini CLI”, “Claude Code”).
Persisted as `Agent` + immutable `AgentVersion`. Pins on a Run via `agent_version_id`.
**Does not** encode model, provider, or API credentials.

### What is an Adapter?

Runtime integration that executes an Agent inside the EvalForge sandbox.
Persisted as `Adapter` + `AdapterVersion`. Normalized key (e.g. `gemini_cli`) resolves via
`AdapterRegistry` + `AdapterCapability`.
**Does not** own inference routing or store secrets.

### What is a Model?

Exact inference model identifier requested (and optionally observed) for a Run
(e.g. `gemini-2.0-flash`). Distinct from Agent and Adapter: the same Agent/Adapter may
run with different models; the same model may later be used by different Agents.

### What is a Provider?

Upstream inference vendor or gateway that supplies model access
(`google`, `openai`, `anthropic`, `groq`, `omniroute`).
`AdapterCapability.provider` today is a **static catalog label**, not a Run pin.

### What is a Gateway?

How EvalForge reaches a provider:

- `direct` — adapter talks to the vendor (current Gemini CLI path)
- `omniroute` — optional OpenAI-compatible gateway in front of many vendors

Gateway is **not** the evaluation engine.

### Where should credentials live?

**Outside** benchmark definitions, Run pins, provenance, logs, events, artifacts, and
user-visible JSON. Today: process environment + sandbox allowlist.

Phase 12 introduces a **credential reference** identity (opaque id + provider key + label).
Secret material stays operator/env-backed (or future vault). Runs may reference
`credential_ref_id` only — never the secret.

### Where should model identity live?

In **execution configuration / metadata** (and derived provenance), not in Suite/Case/
Prompt/Grader benchmark definitions. Optional future: AdapterVersion runtime config —
out of scope unless required for pin-time reproducibility.

### What belongs in Run provenance?

Already: pins, repo SHA, agent/adapter labels, `adapter_key`, execution_mode, metadata,
scores, reproducibility, benchmark_key.

Phase 12 adds (non-secret):

- provider_key, gateway_key
- requested_model, actual_model (honest null if unknown)
- routing_mode (`fixed` | `auto`)
- canonical_evaluation flag
- credential_ref_id (reference only)
- fallback_used when known

### What belongs in benchmark definition?

SuiteVersion composition + case/prompt/grader/platform pins + repository SHA.
**Not** model, provider, gateway, or credentials.

### How should OmniRoute fit?

Optional **provider/gateway** layer for OpenAI-compatible model transport.
EvalForge remains authoritative over benchmark, sandbox, grading, provenance.
OmniRoute must not become the source of truth for scores.

### What must remain EvalForge-owned?

Benchmark definition, task, prompt, repository SHA, sandbox, execution lifecycle,
adapter selection, grading, scores, provenance, reproducibility, comparison.

---

## Current state (inspected)

| Concern | Location | Status |
|---------|----------|--------|
| Agent / Adapter / Platform versions | `domain/.../agent_integration/`, `platform/` | Identity only — no model fields |
| Run pins (7 axes) | `domain/.../execution/run.py` | No model/provider pin |
| Execution configuration | `domain/.../execution/configuration.py` | Mode + allowlisted metadata (adapter/sandbox) |
| Capability registry | `application/.../adapter_capabilities.py` | Static `provider` label; credential env names |
| Worker registry | `workers/.../integration/adapter_registry.py` | Live: `gemini_cli` only; fail closed |
| Gemini adapter | `adapters/.../gemini/` | CLI default model; no `--model` pin |
| Judge providers | `graders/.../providers/` | Separate stack with models in env |
| Provenance | `application/.../dto/provenance.py` | No provider/model/gateway |
| Comparison | `application/.../benchmark.py` | Fairness axes omit model/provider |
| Credentials | `.env` + sandbox allowlist | No BYOK reference abstraction |
| OmniRoute | — | **Absent** |

Allowlisted execution metadata keys today:

```text
adapter_key, adapter_name, adapter_version_id,
sandbox_engine, sandbox_network_mode, worker_adapter_mode_source
```

---

## Gaps Phase 12 must close

1. Typed provider / gateway / model / routing identity (no secrets).
2. Credential **reference** boundary vs secret material.
3. Exact model pinning for canonical (`fixed`) evaluation; `auto` marked non-canonical.
4. No silent fallback / model substitution.
5. OmniRoute as optional OpenAI-compatible gateway behind an interface.
6. Provenance + comparison surfaces for provider/model/gateway/routing.
7. Preserve direct `gemini_cli` + `GEMINI_API_KEY` path unchanged in behavior.
8. Tests without network in CI; gated OmniRoute integration.

## Non-goals

- Credential marketplace UI
- Multi-provider live adapter matrix
- Rewriting Gemini CLI unless required
- Large frontend redesign
- Making OmniRoute mandatory

## Implementation shape (chosen)

```
domain/execution/provider_runtime.py   — enums + value objects
domain/execution/credentials.py        — CredentialReference (no secret)
domain/execution/configuration.py      — extend allowlisted metadata keys
application/provider_runtime/          — resolution, validation, redaction helpers
application/gateways/                  — OpenAI-compatible + OmniRoute config
workers/.../process.py                 — record provider/model identity in metadata
benchmark.py + run_comparison.py       — expected-diff dimensions for model/provider
```

Reuse judge `ProviderConfig` patterns only for transport knobs; do **not** reuse
`JudgeProvider` as the coding-agent gateway.
