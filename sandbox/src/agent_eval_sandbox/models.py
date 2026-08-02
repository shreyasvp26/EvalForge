"""Sandbox Runtime value objects.

No Domain / Application / Adapter / Grader types — isolated execution only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from uuid import uuid4


class SandboxState(StrEnum):
    """Container lifecycle states owned by the Sandbox Runtime."""

    CREATED = "created"
    STARTED = "started"
    STOPPED = "stopped"
    DESTROYED = "destroyed"


class NetworkMode(StrEnum):
    """Network isolation posture for a sandbox."""

    NONE = "none"
    BRIDGE = "bridge"
    CUSTOM = "custom"


class ArtifactKind(StrEnum):
    """Kinds of artifacts the runtime can export."""

    FILE = "file"
    DIRECTORY = "directory"
    LOG = "log"


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Hard resource bounds enforced at the sandbox boundary.

    Numerical defaults are operational starting points, not architecture
    commitments (Execution Engine Architecture — Resource Accounting).
    """

    cpu_cores: float = 1.0
    memory_bytes: int = 512 * 1024 * 1024
    disk_bytes: int | None = 2 * 1024 * 1024 * 1024
    timeout_seconds: float = 300.0


@dataclass(frozen=True, slots=True)
class MountSpec:
    """Host → container filesystem mount."""

    source: str
    target: str
    read_only: bool = False


@dataclass(frozen=True, slots=True)
class NetworkPolicy:
    """Network configuration. Default deny (none) matches System Overview §15."""

    mode: NetworkMode = NetworkMode.NONE
    network_name: str | None = None
    dns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SandboxSpec:
    """Everything required to provision one isolated sandbox."""

    image: str
    working_dir: str = "/workspace"
    environment: Mapping[str, str] = field(default_factory=dict)
    mounts: tuple[MountSpec, ...] = ()
    resources: ResourceLimits = field(default_factory=ResourceLimits)
    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    command: tuple[str, ...] = ("sleep", "infinity")
    labels: Mapping[str, str] = field(default_factory=dict)
    name: str | None = None


@dataclass(frozen=True, slots=True)
class SandboxHandle:
    """Opaque reference to a provisioned sandbox instance."""

    id: str
    container_id: str
    state: SandboxState
    spec: SandboxSpec

    def with_state(self, state: SandboxState) -> SandboxHandle:
        return replace(self, state=state)

    @staticmethod
    def new_id() -> str:
        return str(uuid4())


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """Observed resource consumption for one execute() call."""

    cpu_percent: float | None = None
    memory_bytes: int | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Command to run inside a started sandbox."""

    command: tuple[str, ...]
    working_dir: str | None = None
    environment: Mapping[str, str] | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Outcome of one execute() call."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)


@dataclass(frozen=True, slots=True)
class ArtifactExportRequest:
    """Request to copy a path out of the sandbox."""

    container_path: str
    kind: ArtifactKind = ArtifactKind.FILE
    destination: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactExport:
    """Exported artifact payload (in-memory and/or written to destination)."""

    container_path: str
    kind: ArtifactKind
    size_bytes: int
    content: bytes
    destination: str | None = None
