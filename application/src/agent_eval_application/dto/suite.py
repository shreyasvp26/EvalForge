"""Suite DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.evaluation_management.suite import EvaluationSuite, SuiteVersion


@dataclass(frozen=True, slots=True)
class SuiteCompositionEntryDTO:
    case_version_id: str
    position: int
    case_project_id: str


@dataclass(frozen=True, slots=True)
class SuiteVersionDTO:
    id: str
    suite_id: str
    version_number: int
    status: str
    composition: tuple[SuiteCompositionEntryDTO, ...]
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: SuiteVersion) -> SuiteVersionDTO:
        return cls(
            id=version.id.value,
            suite_id=version.suite_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            composition=tuple(
                SuiteCompositionEntryDTO(
                    case_version_id=entry.case_version_id.value,
                    position=entry.position,
                    case_project_id=entry.case_project_id.value,
                )
                for entry in version.composition
            ),
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class SuiteDTO:
    id: str
    project_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: tuple[SuiteVersionDTO, ...]

    @classmethod
    def from_domain(cls, suite: EvaluationSuite) -> SuiteDTO:
        active = suite.active_version()
        return cls(
            id=suite.id.value,
            project_id=suite.project_id.value,
            name=suite.name,
            description=suite.description,
            status=suite.status.value,
            created_at=suite.created_at,
            active_version_id=active.id.value if active else None,
            versions=tuple(SuiteVersionDTO.from_domain(v) for v in suite.versions),
        )
