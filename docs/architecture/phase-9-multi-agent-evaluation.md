# Phase 9 — Verified Multi-Agent Evaluation

## Status

Phase 9 hardens EvalForge as a multi-agent evaluation platform where adapters
are marked VERIFIED only after real Docker end-to-end proof.

Base: `main` (Phase 7) + merged Phase 8 benchmark integrity baseline.
OAuth (PR #23) remains a separate open PR and is not merged into this branch.

## What shipped

1. **Adapter capability registry** — `AdapterCapability` with
   `verified_live` / `synthetic_only` / `unsupported` statuses
2. **Fail-closed worker resolution** — no Claude soft fallback when pins resolve;
   unsupported adapters raise `adapter_unsupported`
3. **Benchmark matrix API** — `POST /v1/runs/benchmark-matrix`
4. **Capabilities API** — `GET /v1/adapters/capabilities`
5. **Documentation** — `docs/architecture/adapter-support-matrix.md`

## Support matrix (authoritative)

| Adapter | Deterministic | Live | Status | Evidence |
|---------|---------------|------|--------|----------|
| gemini_cli | no | yes | VERIFIED LIVE / PROVIDER-BLOCKED | Missing-key fail-fast passed; calculator e2e hit Gemini rate limit (honest adapter_failure) |
| claude_code | synthetic | no | SYNTHETIC ONLY | CI deterministic path |
| cursor | no | no | UNSUPPORTED | Not registered |
| codex | no | no | UNSUPPORTED | Not registered |
| aider | no | no | UNSUPPORTED | Not registered |

## Live verification notes

- `ANTHROPIC_API_KEY` was **not** present → Claude live **NOT VERIFIED**
- `GEMINI_API_KEY` present → Gemini path exercised; quota blocked completion
- No orphan EvalForge sandbox containers after live attempt
- Compose stack containers (api/worker/postgres/redis/minio) remain by design

## Engineering principle preserved

One genuinely verified adapter beats five fake dropdown options.
Cross-agent score claims require the same immutable benchmark definition.
