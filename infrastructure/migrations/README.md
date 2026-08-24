# Alembic migrations

Revision scripts for the EvalForge PostgreSQL schema.

```bash
# From repository root (script_location is resolved via %(here)s — CWD-safe):
uv run alembic -c infrastructure/alembic.ini upgrade head
uv run alembic -c infrastructure/alembic.ini downgrade -1
uv run alembic -c infrastructure/alembic.ini revision --autogenerate -m "describe change"
```

`env.py` loads ORM models from `agent_eval_infrastructure.database.models`
and resolves `DATABASE_URL` via `DatabaseSettings`.
