# Infrastructure scripts

## Seed Coding Benchmark v1

```bash
# Requires DATABASE_URL / REDIS_URL matching local API + worker.
uv run python infrastructure/scripts/seed_and_run_coding_benchmark.py --allow-all-auth
```

Optional fan-out (after creating a published Gemini agent/adapter):

```bash
uv run python infrastructure/scripts/seed_and_run_coding_benchmark.py \
  --allow-all-auth \
  --execute \
  --agent-id "$AGENT_ID" \
  --agent-version-id "$AGENT_VERSION_ID" \
  --adapter-version-id "$ADAPTER_VERSION_ID"
```

Do not pass provider API keys on the CLI. Live execution uses worker env
(`WORKER_ADAPTER_MODE=live`, `GEMINI_API_KEY`, Docker sandbox).
