# agent-eval-shared

Python cross-cutting foundation for EvalForge (Backend Architecture §11).

## Why this package exists

Every backend module may depend on `shared/`; `shared/` depends on nothing else in the tree. It owns:

| Module   | Responsibility                        |
| -------- | ------------------------------------- |
| `errors` | Typed error hierarchy + serialization |
| `config` | Pydantic Settings loading (fail fast) |
| `log`    | structlog setup + correlation context |
| `utils`  | Correlation IDs and tiny helpers      |

Domain code may use error base types and utilities, but **must not** import `config` or `logging`.

## Usage

```python
from agent_eval_shared import (
    BaseSettings,
    configure_logging,
    create_correlation_id,
    get_logger,
    load_settings,
    bind_context,
)

settings = load_settings()
configure_logging(level=settings.log_level, environment=settings.environment)
bind_context(correlation_id=create_correlation_id())
log = get_logger("api")
log.info("request.accepted")
```
