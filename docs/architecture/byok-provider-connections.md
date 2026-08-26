# BYOK Provider Connections & Exact Model Configuration

Phase 13 turns the Phase 12 provider/model runtime into a usable product path:

Settings → connect provider credential → select exact model on a run →
worker pins the model into the adapter → provenance records identity without secrets.

## Concepts (unchanged)

| Concept | Example |
|---------|---------|
| Agent | Gemini CLI |
| Adapter | `gemini_cli` |
| Model | `gemini-2.0-flash` |
| Provider | `google` |
| Gateway | `direct` |
| Credential | `user:<id>:conn:<id>` or `env:GEMINI_API_KEY` |

OmniRoute remains optional infrastructure — not the evaluation engine.

## Provider connection lifecycle

1. User authenticates.
2. `POST /v1/provider-connections` with `provider_key` + `api_key`.
3. Secret is Fernet-encrypted at rest (`PROVIDER_CREDENTIALS_KEY`).
4. API returns identity + `masked_key` only.
5. Run create references `provider_connection_id` (non-secret).
6. Worker resolves secret only for sandbox injection; never persists it on the Run.
7. `DELETE /v1/provider-connections/{id}` revokes and wipes ciphertext.

## Secret boundary

Never in: provenance, events, logs, artifacts, comparison, Git, API responses after create.

Local/dev: set `PROVIDER_CREDENTIALS_KEY` (≥32 chars). Falls back to `JWT_SECRET_KEY` only for local convenience.

## Exact model pinning

Canonical Gemini path:

```text
CreateRun.model_id → runs.runtime_request.requested_model
  → worker ProviderRuntimeRequest
  → GeminiAdapter(--model <id>)
  → execution_metadata + provenance
```

Unsupported model/provider/gateway combinations fail closed.
`routing_mode=auto` is never canonical.

## Catalog honesty

| Provider | Status |
|----------|--------|
| Google | `live_capable` (gemini_cli + direct) |
| Anthropic | `configurable` (store only; live not verified) |
| OpenAI | `unsupported` for coding-agent runs |
| OmniRoute | `configurable` gateway only |

## APIs

- `GET /v1/providers`
- `GET /v1/models?provider_key=`
- `GET|POST /v1/provider-connections`
- `DELETE /v1/provider-connections/{id}`
- CreateRun accepts optional `provider_key`, `model_id`, `gateway_key`, `routing_mode`, `provider_connection_id`

## UI

- Settings → Providers
- Create Run review: optional Model / Provider / Credential (Gemini path)

## Related

- [Phase 13 audit](./phase-13-byok-model-audit.md)
- [Provider & model runtime](./provider-model-runtime.md)
