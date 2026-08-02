"""EvalForge shared foundation.

Cross-cutting, framework-level concerns with no business meaning:
structured logging, configuration loading, common error base types, and
small utilities. See Backend Architecture §11.
"""

from agent_eval_shared.config import BaseSettings, load_settings
from agent_eval_shared.errors import (
    AppError,
    ApplicationError,
    ConfigurationError,
    InfrastructureError,
    ValidationError,
    serialize_error,
)
from agent_eval_shared.log import (
    bind_context,
    clear_context,
    configure_logging,
    get_context,
    get_logger,
)
from agent_eval_shared.utils import create_correlation_id, invariant

__all__ = [
    "AppError",
    "ApplicationError",
    "BaseSettings",
    "ConfigurationError",
    "InfrastructureError",
    "ValidationError",
    "bind_context",
    "clear_context",
    "configure_logging",
    "create_correlation_id",
    "get_context",
    "get_logger",
    "invariant",
    "load_settings",
    "serialize_error",
]
