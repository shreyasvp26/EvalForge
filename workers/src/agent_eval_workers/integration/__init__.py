"""Worker composition bridges to production Sandbox / Adapter / Graders."""

from __future__ import annotations

from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.sandbox_adapter import ManagedSandboxAdapter

__all__ = [
    "ManagedSandboxAdapter",
    "RunSandboxRegistry",
    "SdkAdapterBridge",
]
