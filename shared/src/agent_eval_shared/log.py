"""Structured logging with correlation context (System Overview §12)."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from agent_eval_shared.config import Environment, LogLevel


def configure_logging(
    *,
    level: LogLevel = "info",
    environment: Environment = "development",
    service_name: str = "evalforge",
) -> None:
    """Configure structlog + stdlib logging once at process startup."""
    del service_name  # reserved for future service binding on root logger name
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "production":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=environment != "test")

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.CRITICAL if environment == "test" else log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind correlation fields for the current context (API/Worker entry)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context vars (end of request/task)."""
    structlog.contextvars.clear_contextvars()


def get_context() -> dict[str, Any]:
    """Return the currently bound context vars."""
    return dict(structlog.contextvars.get_contextvars())
