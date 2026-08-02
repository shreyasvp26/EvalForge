"""EvalForge shared foundation.

Cross-cutting, framework-level concerns with no business meaning:
structured logging, metrics, tracing, configuration loading, common error
base types, and small utilities. See Backend Architecture §11.
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
from agent_eval_shared.metrics import (
    configure_metrics,
    get_metrics,
    observe_adapter_run,
    observe_execution_step,
    observe_grader_run,
    observe_http_request,
    observe_worker_task,
    render_metrics,
)
from agent_eval_shared.tracing import (
    configure_tracing,
    get_tracer,
    shutdown_tracing,
    start_span,
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
    "configure_metrics",
    "configure_tracing",
    "create_correlation_id",
    "get_context",
    "get_logger",
    "get_metrics",
    "get_tracer",
    "invariant",
    "load_settings",
    "observe_adapter_run",
    "observe_execution_step",
    "observe_grader_run",
    "observe_http_request",
    "observe_worker_task",
    "render_metrics",
    "serialize_error",
    "shutdown_tracing",
    "start_span",
]
