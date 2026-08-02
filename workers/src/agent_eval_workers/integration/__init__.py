"""Worker composition bridges to production Sandbox / Adapter / Graders."""

from __future__ import annotations

from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.composition import (
    ProductionHarness,
    build_production_harness,
    default_claude_factory,
    rebuild_production_worker,
)
from agent_eval_workers.integration.grading_scheduler import (
    GraderInvocationSpec,
    GraderSdkScheduler,
)
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.sandbox_adapter import ManagedSandboxAdapter

__all__ = [
    "GraderInvocationSpec",
    "GraderSdkScheduler",
    "ManagedSandboxAdapter",
    "ProductionHarness",
    "RunSandboxRegistry",
    "SdkAdapterBridge",
    "build_production_harness",
    "default_claude_factory",
    "rebuild_production_worker",
]
