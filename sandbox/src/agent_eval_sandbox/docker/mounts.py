"""Docker bind-mount translation."""

from __future__ import annotations

from typing import Any

from agent_eval_sandbox.models import MountSpec


def build_mounts(mounts: tuple[MountSpec, ...]) -> list[dict[str, Any]]:
    """Convert mount specs to Docker mount dictionaries."""
    result: list[dict[str, Any]] = []
    for mount in mounts:
        if not mount.source or not mount.target:
            raise ValueError("mount source and target must be non-empty")
        result.append(
            {
                "Type": "bind",
                "Source": mount.source,
                "Target": mount.target,
                "ReadOnly": mount.read_only,
            }
        )
    return result


def workspace_mount(host_path: str, *, target: str = "/workspace") -> MountSpec:
    """Convenience: writable repository mount at the sandbox working directory."""
    return MountSpec(source=host_path, target=target, read_only=False)


def readonly_mount(host_path: str, target: str) -> MountSpec:
    """Convenience: read-only host path (tools, caches, reference trees)."""
    return MountSpec(source=host_path, target=target, read_only=True)
