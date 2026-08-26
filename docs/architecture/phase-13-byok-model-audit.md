# Phase 13 — BYOK Provider Connections & Exact Model Configuration Audit

**Branch:** `feat/phase-13-byok-model-configuration`  
**Base:** `main` @ Phase 12 merge (`ef74e88` / PR #27)  
**Principle:** Extend Phase 12. Do not duplicate or collapse Agent / Adapter / Model / Provider / Credential / Gateway.

## 1. Existing provider/model abstractions (Phase 12)

| Type | Path | Role |
|------|------|------|
| `ProviderKey`, `GatewayKey`, `RoutingMode`, `ModelId`, `ModelIdentity`, `ProviderRuntimeIdentity` | `domain/.../execution/provider_runtime.py` | Runtime identity VOs |
| `CredentialReference`, `CredentialBackend`, `CredentialSecretResolver` | `domain/.../execution/credentials.py` | Identity without secret |
| `resolve_provider_runtime`, `DEFAULT_ENV_CREDENTIAL_REFS` | `application/.../provider_runtime/` | Validation + env catalog |
| `EnvCredentialSecretResolver`, `OpenAICompatibleGateway` | `application/.../gateways/` | Optional OmniRoute transport |
| Allowlisted metadata keys | `domain/.../execution/configuration.py` | Persist non-secret identity |

**Reuse these.** Do not invent parallel Provider/Model aggregates.

## 2. Existing credential boundary

- Secrets live only in process environment today.
- Runs may store `credential_ref_id` (e.g. `env:GEMINI_API_KEY`).
- Sandbox gets keys via `WORKER_SANDBOX_ENV_ALLOWLIST` — never full host environ.
- `CredentialBackend.ENVIRONMENT` is implemented; comments reserve future `USER_SECRET_STORE`.

## 3. Current secret-resolution path

```text
Operator env → EnvCredentialSecretResolver / sandbox allowlist
             → Adapter / OmniRoute gateway
             → Never provenance / API / logs
```

Coding-agent path does **not** use `EnvCredentialSecretResolver`; Gemini uses allowlisted sandbox env.

## 4. Current Gemini model-resolution path

`GeminiAdapter` (`adapters/.../gemini/adapter.py`):
- Args: `--skip-trust --yolo --output-format stream-json -p <prompt>`
- **No `--model`** — CLI default applies
- Worker may record `EVALFORGE_MODEL` / `GEMINI_MODEL` in metadata while CLI ignores it → integrity gap

Judge `GEMINI_MODEL` is a separate plane and must not be conflated.

## 5. Missing user-facing provider connection functionality

- No `ProviderConnection` entity / table
- No user-scoped credential ownership
- No Settings “Model Providers” UI
- No CRUD API for connections
- No encrypted / user secret store (only env)

## 6. Missing exact model pinning

- No model catalog
- `CreateRun` has no provider/model/credential/gateway/routing fields
- Create-run UI: Project → Case → Prompt → Agent → Graders → Review (no model step)
- Gemini CLI not passed an exact model

## 7. Required changes (Phase 13)

| Layer | Change |
|-------|--------|
| Domain | `ProviderConnection` VO (non-secret); extend `CredentialBackend` with `USER_SECRET_STORE` |
| Application | Connection CRUD, ownership checks, model catalog, CreateRun runtime fields |
| Infrastructure | Migration + ORM + Fernet-encrypted secret column (or equivalent smallest store) |
| Worker | Resolve connection → inject secret ephemerally; pass model to Gemini CLI |
| Adapter | `GeminiAdapter` honors exact `--model` |
| API | `/v1/providers`, `/v1/provider-connections`, model catalog; extend CreateRun |
| Web | Settings Model Providers; run config selectors |

## 8. Security risks

| Risk | Mitigation |
|------|------------|
| Plaintext API keys in DB | Encrypt at rest; never return plaintext after create |
| Cross-user credential use | User-scoped ownership; authorize on every resolve |
| Secrets in provenance/events | Allowlist + redaction tests |
| Deleted connection still usable | Soft-delete / status=revoked; fail closed on resolve |
| Sandbox secret persistence | Ephemeral env inject only; existing allowlist pattern |
| Advertising unsupported providers | Catalog marks live-capable vs unsupported honestly |

## 9. Test plan

1. Domain ProviderConnection + redaction  
2. Application ownership / delete / resolve  
3. API create/list/delete never echoes secret  
4. Model catalog + unsupported combo fail-closed  
5. Exact Gemini `--model` reaches adapter invocation  
6. No silent fallback when model requested  
7. Provenance records identity without secrets  
8. Comparison surfaces model/provider diffs  
9. Frontend unit tests + typecheck + build  
10. Docker / live Gemini / OmniRoute: VERIFIED only if available; else honest BLOCKED/NOT VERIFIED  

## Non-goals

Credential marketplace, EvalForge-paid inference, OmniRoute rewrite, GitHub PR-on-pass, fake live adapters, UI redesign.
