"""Case and Prompt DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.evaluation_management.case import (
    CaseVersion,
    EvaluationCase,
    PromptVersion,
)


@dataclass(frozen=True, slots=True)
class PromptVersionDTO:
    id: str
    prompt_id: str
    version_number: int
    status: str
    content: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: PromptVersion) -> PromptVersionDTO:
        return cls(
            id=version.id.value,
            prompt_id=version.prompt_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            content=version.content,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class CaseVersionDTO:
    id: str
    case_id: str
    version_number: int
    status: str
    description: str
    repository_url: str
    commit_sha: str
    subdirectory: str | None
    expected_checks: tuple[str, ...]
    applicable_grader_ids: tuple[str, ...]
    prompt_version_id: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: CaseVersion) -> CaseVersionDTO:
        return cls(
            id=version.id.value,
            case_id=version.case_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            description=version.description,
            repository_url=version.reference_repository.repository_url,
            commit_sha=version.reference_repository.commit_sha,
            subdirectory=version.reference_repository.subdirectory,
            expected_checks=tuple(version.expected_checks),
            applicable_grader_ids=tuple(g.value for g in version.applicable_grader_ids),
            prompt_version_id=version.prompt_version_id.value,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class CaseDTO:
    id: str
    project_id: str
    prompt_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    active_version_id: str | None
    active_prompt_version_id: str | None
    versions: tuple[CaseVersionDTO, ...]
    prompt_versions: tuple[PromptVersionDTO, ...]

    @classmethod
    def from_domain(cls, case: EvaluationCase) -> CaseDTO:
        active = case.active_version()
        active_prompt = case.prompt.active_version()
        return cls(
            id=case.id.value,
            project_id=case.project_id.value,
            prompt_id=case.prompt.id.value,
            name=case.name,
            description=case.description,
            status=case.status.value,
            created_at=case.created_at,
            active_version_id=active.id.value if active else None,
            active_prompt_version_id=(
                active_prompt.id.value if active_prompt else None
            ),
            versions=tuple(CaseVersionDTO.from_domain(v) for v in case.versions),
            prompt_versions=tuple(
                PromptVersionDTO.from_domain(v) for v in case.prompt.versions
            ),
        )
