"""Platform catalog DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.platform.platform import Platform, PlatformVersion


@dataclass(frozen=True, slots=True)
class PlatformVersionDTO:
    id: str
    platform_id: str
    version_number: int
    status: str
    label: str
    sandbox_policy: dict[str, str]
    execution_policy: dict[str, str]
    timeout_policy: dict[str, str]
    environment_policy: dict[str, str]
    grading_policy: dict[str, str]
    notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: PlatformVersion) -> PlatformVersionDTO:
        return cls(
            id=version.id.value,
            platform_id=version.platform_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            label=version.label,
            sandbox_policy=dict(version.sandbox_policy),
            execution_policy=dict(version.execution_policy),
            timeout_policy=dict(version.timeout_policy),
            environment_policy=dict(version.environment_policy),
            grading_policy=dict(version.grading_policy),
            notes=version.notes,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class PlatformDTO:
    id: str
    name: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: tuple[PlatformVersionDTO, ...]

    @classmethod
    def from_domain(cls, platform: Platform) -> PlatformDTO:
        active = platform.active_version()
        return cls(
            id=platform.id.value,
            name=platform.name,
            status=platform.status.value,
            created_at=platform.created_at,
            active_version_id=active.id.value if active else None,
            versions=tuple(
                PlatformVersionDTO.from_domain(version) for version in platform.versions
            ),
        )
