"""Worker composition bridges to production Sandbox / Adapter / Graders."""

from __future__ import annotations

from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.adapter_registry import (
    AdapterRegistry,
    AdapterResolutionError,
    PinnedAdapterResolver,
    default_adapter_registry,
    normalize_adapter_key,
    resolve_adapter_mode,
)
from agent_eval_workers.integration.composition import (
    ProductionHarness,
    build_production_harness,
    default_claude_factory,
    rebuild_production_worker,
)
from agent_eval_workers.integration.grader_resolver import PinBasedGraderResolver
from agent_eval_workers.integration.grading_scheduler import (
    GraderInvocationSpec,
    GraderSdkScheduler,
)
from agent_eval_workers.integration.process import (
    ProductionWorkerBundle,
    build_production_lifecycle_factory,
    build_production_worker,
    select_adapter_factory,
    select_docker_engine,
)
from agent_eval_workers.integration.prompt_resolver import PinnedPromptResolver
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.sandbox_adapter import ManagedSandboxAdapter
from agent_eval_workers.integration.worker_auth import WorkerAuthorization

__all__ = [
    "AdapterRegistry",
    "AdapterResolutionError",
    "GraderInvocationSpec",
    "GraderSdkScheduler",
    "ManagedSandboxAdapter",
    "PinBasedGraderResolver",
    "PinnedAdapterResolver",
    "PinnedPromptResolver",
    "ProductionHarness",
    "ProductionWorkerBundle",
    "RunSandboxRegistry",
    "SdkAdapterBridge",
    "WorkerAuthorization",
    "build_production_harness",
    "build_production_lifecycle_factory",
    "build_production_worker",
    "default_adapter_registry",
    "default_claude_factory",
    "normalize_adapter_key",
    "rebuild_production_worker",
    "resolve_adapter_mode",
    "select_adapter_factory",
    "select_docker_engine",
]
