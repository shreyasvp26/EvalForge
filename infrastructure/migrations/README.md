# Alembic migrations

Revision scripts for the EvalForge PostgreSQL schema.

```bash
# From repository root (or infrastructure/):
cd infrastructure
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic revision --autogenerate -m "describe change"
```

`env.py` loads ORM models from `agent_eval_infrastructure.database.models`
and resolves `DATABASE_URL` via `DatabaseSettings`.
