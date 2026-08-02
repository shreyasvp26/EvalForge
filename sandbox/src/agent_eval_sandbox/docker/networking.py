"""Docker networking policy translation.

Default posture is deny-all (``NetworkMode.NONE``), matching System Overview
security isolation requirements.
"""

from __future__ import annotations

from typing import Any

from agent_eval_sandbox.exceptions import SandboxProvisionError
from agent_eval_sandbox.models import NetworkMode, NetworkPolicy


def resolve_network(
    policy: NetworkPolicy,
) -> tuple[str | None, dict[str, Any] | None, list[str] | None]:
    """Return ``(network_mode, networking_config, dns)`` for container create.

    ``network_mode`` is used for ``none`` / ``bridge``. Custom networks set
    ``networking_config`` instead and leave ``network_mode`` as ``None``.
    """
    dns = list(policy.dns) if policy.dns else None

    if policy.mode is NetworkMode.NONE:
        return "none", None, dns

    if policy.mode is NetworkMode.BRIDGE:
        return "bridge", None, dns

    if policy.mode is NetworkMode.CUSTOM:
        if not policy.network_name:
            raise SandboxProvisionError(
                "NetworkMode.CUSTOM requires network_name",
                details={"mode": policy.mode.value},
                retryable=False,
            )
        networking_config = {
            "EndpointsConfig": {
                policy.network_name: {},
            }
        }
        return None, networking_config, dns

    raise SandboxProvisionError(
        f"Unsupported network mode: {policy.mode!r}",
        details={"mode": str(policy.mode)},
        retryable=False,
    )
