"""EvalForge Sandbox Runtime.

Isolated execution only. This package provisions containers, mounts
repositories, injects environment, enforces resource limits, runs commands,
collects stdout/stderr/artifacts, and always cleans up.

It must NOT know Domain, Application, Execution Engine, Adapter, or Grader
logic (Execution Engine Architecture — Sandbox Lifecycle).
"""

from __future__ import annotations

from agent_eval_sandbox.docker import DockerPyEngine, DockerSandbox
from agent_eval_sandbox.exceptions import (
    SandboxCleanupError,
    SandboxCopyError,
    SandboxError,
    SandboxExecutionError,
    SandboxNotFoundError,
    SandboxProvisionError,
    SandboxStateError,
    SandboxTimeoutError,
)
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import (
    ArtifactExport,
    ArtifactExportRequest,
    ArtifactKind,
    ExecutionRequest,
    ExecutionResult,
    MountSpec,
    NetworkMode,
    NetworkPolicy,
    ResourceLimits,
    ResourceUsage,
    SandboxHandle,
    SandboxSpec,
    SandboxState,
)
from agent_eval_sandbox.ports import DockerEngine, SandboxRuntime

__all__ = [
    "ArtifactExport",
    "ArtifactExportRequest",
    "ArtifactKind",
    "DockerEngine",
    "DockerPyEngine",
    "DockerSandbox",
    "ExecutionRequest",
    "ExecutionResult",
    "MountSpec",
    "NetworkMode",
    "NetworkPolicy",
    "ResourceLimits",
    "ResourceUsage",
    "SandboxCleanupError",
    "SandboxCopyError",
    "SandboxError",
    "SandboxExecutionError",
    "SandboxHandle",
    "SandboxManager",
    "SandboxNotFoundError",
    "SandboxProvisionError",
    "SandboxRuntime",
    "SandboxSpec",
    "SandboxState",
    "SandboxStateError",
    "SandboxTimeoutError",
]
