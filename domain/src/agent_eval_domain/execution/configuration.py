"""Execution mode and safe execution metadata recorded on a Run."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_domain.common.errors import InvariantViolation

# Keys allowed in persisted execution_metadata. Never include secrets / env values.
ALLOWED_EXECUTION_METADATA_KEYS = frozenset(
    {
        "adapter_key",
        "adapter_name",
        "adapter_version_id",
        "sandbox_engine",
        "sandbox_network_mode",
        "worker_adapter_mode_source",
        # Phase 12 — provider / model / gateway identity (non-secret)
        "provider_key",
        "gateway_key",
        "requested_model",
        "actual_model",
        "routing_mode",
        "canonical_evaluation",
        "credential_ref_id",
        "fallback_used",
    }
)


class ExecutionMode(StrEnum):
    """How the coding agent was actually executed for this Run."""

    DETERMINISTIC = "deterministic"
    LIVE = "live"


def sanitize_execution_metadata(
    metadata: dict[str, str] | None,
) -> dict[str, str]:
    """Keep only allowlisted non-secret string metadata."""
    if not metadata:
        return {}
    cleaned: dict[str, str] = {}
    for raw_key, raw_value in metadata.items():
        key = str(raw_key).strip()
        if key not in ALLOWED_EXECUTION_METADATA_KEYS:
            continue
        value = str(raw_value).strip()
        if not value:
            continue
        # Defensive: never persist values that look like credentials.
        if any(
            marker in value.lower()
            for marker in ("sk-", "api_key=", "bearer ", "password=")
        ):
            continue
        cleaned[key] = value
    return cleaned


@dataclass(frozen=True, slots=True)
class ExecutionConfiguration:
    """Effective execution configuration used for a Run (no secrets)."""

    mode: ExecutionMode
    metadata: dict[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            sanitize_execution_metadata(dict(self.metadata)),
        )
        if not isinstance(self.mode, ExecutionMode):
            raise InvariantViolation(
                "execution_mode must be deterministic or live",
                code="INVALID_EXECUTION_MODE",
            )
