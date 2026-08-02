"""Grader DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.grading.grader import Grader, GraderVersion


@dataclass(frozen=True, slots=True)
class GraderVersionDTO:
    id: str
    grader_id: str
    version_number: int
    status: str
    label: str
    specification: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: GraderVersion) -> GraderVersionDTO:
        return cls(
            id=version.id.value,
            grader_id=version.grader_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            label=version.label,
            specification=version.specification,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class GraderDTO:
    id: str
    name: str
    family: str
    description: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: tuple[GraderVersionDTO, ...]

    @classmethod
    def from_domain(cls, grader: Grader) -> GraderDTO:
        active = grader.active_version()
        return cls(
            id=grader.id.value,
            name=grader.name,
            family=grader.family.value,
            description=grader.description,
            status=grader.status.value,
            created_at=grader.created_at,
            active_version_id=active.id.value if active else None,
            versions=tuple(GraderVersionDTO.from_domain(v) for v in grader.versions),
        )
