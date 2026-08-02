"""Version number and lineage value objects."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import EntityId
from agent_eval_domain.versioning.status import VersionStatus


@dataclass(frozen=True, slots=True)
class VersionNumber:
    """Monotonic version number within a parent identity (1-based)."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvariantViolation(
                "Version number must be >= 1",
                code="INVALID_VERSION_NUMBER",
                details={"value": self.value},
            )

    def next(self) -> VersionNumber:
        return VersionNumber(self.value + 1)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class VersionRef[TId: EntityId]:
    """Immutable pointer to a specific version of a versioned entity."""

    version_id: TId
    version_number: VersionNumber
    status: VersionStatus
    predecessor_version_id: TId | None = None

    def is_pinnable(self) -> bool:
        """Draft versions cannot be pinned by a Run."""
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}
