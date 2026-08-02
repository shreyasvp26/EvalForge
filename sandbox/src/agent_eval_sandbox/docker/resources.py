"""Docker host-config resource limit translation."""

from __future__ import annotations

from typing import Any

from agent_eval_sandbox.models import ResourceLimits

# 1 CPU core = 1e9 nano_cpus in Docker.
_NANO_CPUS_PER_CORE = 1_000_000_000


def build_resource_host_config(limits: ResourceLimits) -> dict[str, Any]:
    """Map ``ResourceLimits`` onto Docker ``HostConfig`` fields."""
    if limits.cpu_cores <= 0:
        raise ValueError("cpu_cores must be > 0")
    if limits.memory_bytes <= 0:
        raise ValueError("memory_bytes must be > 0")
    if limits.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")

    config: dict[str, Any] = {
        "NanoCpus": int(limits.cpu_cores * _NANO_CPUS_PER_CORE),
        "Memory": int(limits.memory_bytes),
        "MemorySwap": int(limits.memory_bytes),  # disable swap beyond memory
        "PidsLimit": 256,
    }
    if limits.disk_bytes is not None:
        if limits.disk_bytes <= 0:
            raise ValueError("disk_bytes must be > 0 when set")
        # Best-effort disk budget via storage opt (driver-dependent).
        config["StorageOpt"] = {"size": str(limits.disk_bytes)}
    return config


def sample_resource_usage(stats: dict[str, object], *, duration_seconds: float):
    """Derive a ``ResourceUsage`` snapshot from Docker stats JSON."""
    from agent_eval_sandbox.models import ResourceUsage

    memory_bytes: int | None = None
    cpu_percent: float | None = None

    memory_stats = stats.get("memory_stats")
    if isinstance(memory_stats, dict):
        usage = memory_stats.get("usage")
        if isinstance(usage, (int, float)):
            memory_bytes = int(usage)

    cpu_stats = stats.get("cpu_stats")
    precpu_stats = stats.get("precpu_stats")
    if isinstance(cpu_stats, dict) and isinstance(precpu_stats, dict):
        cpu_percent = _cpu_percent(cpu_stats, precpu_stats)

    return ResourceUsage(
        cpu_percent=cpu_percent,
        memory_bytes=memory_bytes,
        duration_seconds=duration_seconds,
    )


def _cpu_percent(
    cpu_stats: dict[str, object],
    precpu_stats: dict[str, object],
) -> float | None:
    total = _cpu_total(cpu_stats)
    pre_total = _cpu_total(precpu_stats)
    system = cpu_stats.get("system_cpu_usage")
    pre_system = precpu_stats.get("system_cpu_usage")
    if not isinstance(total, int) or not isinstance(pre_total, int):
        return None
    if not isinstance(system, int) or not isinstance(pre_system, int):
        return None
    cpu_delta = total - pre_total
    system_delta = system - pre_system
    if cpu_delta <= 0 or system_delta <= 0:
        return 0.0
    online = _online_cpus(cpu_stats)
    return (cpu_delta / system_delta) * online * 100.0


def _cpu_total(cpu_stats: dict[str, object]) -> int | None:
    usage = cpu_stats.get("cpu_usage")
    if not isinstance(usage, dict):
        return None
    total = usage.get("total_usage")
    return int(total) if isinstance(total, (int, float)) else None


def _online_cpus(cpu_stats: dict[str, object]) -> int:
    online = cpu_stats.get("online_cpus")
    if isinstance(online, int) and online > 0:
        return online
    usage = cpu_stats.get("cpu_usage")
    if isinstance(usage, dict):
        percpu = usage.get("percpu_usage")
        if isinstance(percpu, list) and percpu:
            return len(percpu)
    return 1
