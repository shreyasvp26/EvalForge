"""EvalForge Adapter Layer.

Translates coding-agent native behavior into the Normalized Domain Model.
Depends only on Domain (NDM shapes), Shared, and Sandbox — never Application,
Infrastructure, Workers, Execution Engine, Graders, or FastAPI.
"""

from __future__ import annotations

from agent_eval_adapters.sdk import (
    Adapter,
    AdapterCapabilities,
    AdapterError,
    AdapterOutcome,
    EventEmitter,
    ExecutionConfig,
    ExecutionContext,
    NativeObservation,
    run_adapter,
)

__all__ = [
    "Adapter",
    "AdapterCapabilities",
    "AdapterError",
    "AdapterOutcome",
    "EventEmitter",
    "ExecutionConfig",
    "ExecutionContext",
    "NativeObservation",
    "run_adapter",
]
