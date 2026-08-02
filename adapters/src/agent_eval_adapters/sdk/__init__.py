"""Adapter SDK — shared contracts and runtime for all vendor adapters."""

from __future__ import annotations

from agent_eval_adapters.sdk.adapter import Adapter, BaseAdapter
from agent_eval_adapters.sdk.capabilities import AdapterCapabilities
from agent_eval_adapters.sdk.context import ExecutionConfig, ExecutionContext
from agent_eval_adapters.sdk.emitter import EventEmitter
from agent_eval_adapters.sdk.exceptions import (
    AdapterCancellationError,
    AdapterError,
    AdapterInitializationError,
    AdapterTimeoutError,
    AdapterTranslationError,
    MalformedOutputError,
)
from agent_eval_adapters.sdk.execution import AdapterResult, run_adapter
from agent_eval_adapters.sdk.lifecycle import AdapterPhase, LifecycleDriver
from agent_eval_adapters.sdk.models import (
    AdapterOutcome,
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
    NativeObservation,
    ObservationKind,
    RunMetadata,
)
from agent_eval_adapters.sdk.ports import (
    AdapterLogger,
    CancellationPort,
    EventSink,
    SandboxExecPort,
)
from agent_eval_adapters.sdk.translator import DefaultTranslator, Translator

__all__ = [
    "Adapter",
    "AdapterCancellationError",
    "AdapterCapabilities",
    "AdapterError",
    "AdapterInitializationError",
    "AdapterOutcome",
    "AdapterPhase",
    "AdapterResult",
    "AdapterTimeoutError",
    "AdapterTranslationError",
    "AdapterLogger",
    "BaseAdapter",
    "CancellationPort",
    "DefaultTranslator",
    "EmittedArtifact",
    "EmittedEvent",
    "EmittedProgress",
    "EventEmitter",
    "EventSink",
    "ExecutionConfig",
    "ExecutionContext",
    "LifecycleDriver",
    "MalformedOutputError",
    "NativeObservation",
    "ObservationKind",
    "RunMetadata",
    "SandboxExecPort",
    "Translator",
    "run_adapter",
]
