# Provider & Model Runtime

Phase 12 foundation for multi-provider, model-aware coding-agent evaluation.

EvalForge evaluates **agents** on **benchmarks**. Providers and gateways only
supply **model access**. They never own scores, graders, sandbox lifecycle, or
benchmark definitions.

## Core entities

| Concept | Meaning | Owned by |
|---------|---------|----------|
| **Benchmark** | SuiteVersion + case/prompt/grader/platform pins + repo SHA | EvalForge |
| **Run** | One evaluation attempt with pinned versions + execution identity | EvalForge |
| **Agent** | Product coding agent (e.g. Gemini CLI) | EvalForge catalog |
| **Adapter** | Runtime integration key (e.g. `gemini_cli`) | EvalForge registry |
| **Model** | Exact inference model id (requested / actual) | Execution identity |
| **Provider** | Upstream vendor (`google`, `openai`, …) or `omniroute` | Execution identity |
| **Gateway** | How inference is reached (`direct` / `omniroute`) | Execution identity |
| **Credential** | Opaque reference to secret material (never the secret) | Operator / BYOK |

Do **not** collapse Agent ≡ Adapter ≡ Model ≡ Provider.

### Same agent, different model

```text
Agent: Gemini CLI  +  Adapter: gemini_cli  +  Model: gemini-2.0-flash
Agent: Gemini CLI  +  Adapter: gemini_cli  +  Model: gemini-1.5-pro
```

### Same model, different agent (future)

```text
Agent: Claude Code  +  Adapter: claude_code  +  Model: claude-sonnet-4-…
Agent: Cursor       +  Adapter: cursor       +  Model: claude-sonnet-4-…
```

## Relationship diagram

```text
Benchmark
   ↓
Run
   ↓
Agent ──→ Adapter
             ↓
           Model
             ↓
      Provider / Gateway
             ↓
         Inference
```

EvalForge remains authoritative above the inference layer:

```text
EvalForge owns:  Benchmark · Task · Prompt · Agent · Adapter · Sandbox ·
                 Artifacts · Grading · Scores · Provenance · Comparison

Provider/Gateway owns:  Model access / routing only
```

## BYOK credential boundary

```text
User
 ↓
Provider Connection   (future UI / API)
 ↓
Credential Reference  (id + provider_key + label + backend)
 ↓
Run execution         (resolves secret at worker/gateway only)
 ↓
Provider / Gateway
```

### Rules

- Benchmark definitions never embed secrets.
- Provenance, API responses, logs, events, artifacts, and comparison payloads
  may include `credential_ref_id` and env **names** only.
- Secret material stays in process environment (Phase 12) or a future vault.
- Default operator refs: `env:GEMINI_API_KEY`, `env:OMNIROUTE_API_KEY`, etc.

## Routing modes (benchmark integrity)

| Mode | Model | Canonical? | Use |
|------|-------|------------|-----|
| `fixed` | Exact model id required | Yes (if no fallback) | Official benchmark results |
| `auto` | Gateway may choose | **Never** | Experimentation only |

- Auto routing is disabled unless `EVALFORGE_ALLOW_AUTO_ROUTING=1`.
- Never silently convert `model=A` into `model=B` or `auto`.
- Unsupported provider/model/gateway combinations **fail closed**.
- When the provider reports an actual model, provenance records both
  `requested_model` and `actual_model`. If unknown, `actual_model` stays null —
  never fabricated.

Legacy direct Gemini without an explicit model pin records
`requested_model=provider-default` and `canonical_evaluation=false`.

## Direct provider execution

```text
EVALFORGE_GATEWAY=direct
EVALFORGE_PROVIDER=google
EVALFORGE_MODEL=gemini-2.0-flash
EVALFORGE_ROUTING_MODE=fixed

Worker → AdapterRegistry(gemini_cli) → Gemini CLI in Docker sandbox
       → GEMINI_API_KEY via sandbox allowlist
       → provenance: provider=google, gateway=direct, model=…
```

This path remains the production coding-agent path. OmniRoute is not required.

## OmniRoute (optional)

```text
EvalForge → OmniRoute (OpenAI-compatible) → upstream provider/model
                ↑
         OMNIROUTE_BASE_URL
         OMNIROUTE_API_KEY  (via credential ref env:OMNIROUTE_API_KEY)
```

Why optional:

- Existing Gemini CLI + direct Google credentials must keep working.
- Public BYOK can later choose direct vendors **or** a gateway.
- OmniRoute must not become the source of truth for scores or provenance.

Configuration (see `.env.example`):

```bash
# OMNIROUTE_BASE_URL=https://your-omniroute-endpoint.example
# OMNIROUTE_API_KEY=
# EVALFORGE_GATEWAY=omniroute
# EVALFORGE_MODEL=<exact-model-id>
# EVALFORGE_ROUTING_MODE=fixed
```

Gated integration test:

```bash
EVALFORGE_OMNIROUTE_INTEGRATION=1 \
OMNIROUTE_BASE_URL=... \
OMNIROUTE_API_KEY=... \
EVALFORGE_OMNIROUTE_MODEL=<exact-model-id> \
uv run --project application pytest application/tests/test_omniroute_integration.py
```

## Comparability

Benchmark fairness (must match): case, prompt, platform, graders, repository SHA.

Expected to differ (explicitly surfaced): agent, adapter, execution_mode,
**provider_key**, **gateway_key**, **requested_model**, **routing_mode**,
**canonical_evaluation**.

Two runs on the same benchmark with different models remain comparable as a
cross-model comparison — they are **not** identical executions.

## Key modules

| Module | Role |
|--------|------|
| `domain/.../execution/provider_runtime.py` | Identity value objects |
| `domain/.../execution/credentials.py` | CredentialReference (no secrets) |
| `domain/.../execution/configuration.py` | Allowlisted execution metadata |
| `application/.../provider_runtime/` | Resolution + validation |
| `application/.../gateways/` | OpenAI-compatible + OmniRoute |
| `workers/.../integration/process.py` | Records runtime identity on Runs |

## Related docs

- [Phase 12 audit](./phase-12-provider-model-runtime-audit.md)
- [Adapter support matrix](./adapter-support-matrix.md)
- [Phase 8 benchmark integrity](./phase-8-benchmark-integrity.md)
- [How EvalForge evaluates coding agents](./how-evalforge-evaluates-coding-agents.md)
