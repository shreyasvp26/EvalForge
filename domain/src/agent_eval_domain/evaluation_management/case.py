"""Evaluation Case aggregate — Case, Case Versions, Prompt, Prompt Versions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvalidStateTransition, InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import (
    CaseId,
    CaseVersionId,
    GraderId,
    ProjectId,
    PromptId,
    PromptVersionId,
)
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)


@dataclass(frozen=True, slots=True)
class ReferenceRepositoryState:
    """Point-in-time reference checkout the Execution Engine must materialize."""

    repository_url: str
    commit_sha: str
    subdirectory: str | None = None

    def __post_init__(self) -> None:
        if not self.repository_url.strip():
            raise InvariantViolation(
                "Reference repository URL must be non-empty",
                code="INVALID_REFERENCE_REPO",
            )
        if not self.commit_sha.strip():
            raise InvariantViolation(
                "Reference commit SHA must be non-empty",
                code="INVALID_REFERENCE_COMMIT",
            )


@dataclass(frozen=True, slots=True)
class PromptVersion:
    id: PromptVersionId
    prompt_id: PromptId
    version_number: VersionNumber
    status: VersionStatus
    content: str
    predecessor_version_id: PromptVersionId | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise InvariantViolation(
                "Prompt Version content must be non-empty",
                code="INVALID_PROMPT_CONTENT",
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class Prompt:
    """Stable Prompt identity belonging to exactly one Case."""

    id: PromptId
    case_id: CaseId
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[PromptVersion] = field(default_factory=list, repr=False)

    @property
    def versions(self) -> tuple[PromptVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> PromptVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: PromptVersionId) -> PromptVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Prompt version {version_id} not found",
            code="PROMPT_VERSION_NOT_FOUND",
            details={"prompt_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: PromptVersionId,
        content: str,
        created_at: datetime | None = None,
    ) -> PromptVersion:
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = PromptVersion(
            id=version_id,
            prompt_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            content=content,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: PromptVersionId) -> PromptVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="PromptVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(
                current,
                PromptVersion(
                    id=current.id,
                    prompt_id=current.prompt_id,
                    version_number=current.version_number,
                    status=VersionStatus.SUPERSEDED,
                    content=current.content,
                    predecessor_version_id=current.predecessor_version_id,
                    created_at=current.created_at,
                ),
            )
        published = PromptVersion(
            id=draft.id,
            prompt_id=draft.prompt_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            content=draft.content,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace(draft, published)
        return published

    def _replace(self, old: PromptVersion, new: PromptVersion) -> None:
        self._versions[self._versions.index(old)] = new


@dataclass(frozen=True, slots=True)
class CaseVersion:
    """Immutable task definition + grader declarations."""

    id: CaseVersionId
    case_id: CaseId
    version_number: VersionNumber
    status: VersionStatus
    description: str
    reference_repository: ReferenceRepositoryState
    expected_checks: tuple[str, ...]
    applicable_grader_ids: tuple[GraderId, ...]
    prompt_version_id: PromptVersionId
    predecessor_version_id: CaseVersionId | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise InvariantViolation(
                "Case Version description must be non-empty",
                code="INVALID_CASE_DESCRIPTION",
            )
        if len(self.applicable_grader_ids) != len(set(self.applicable_grader_ids)):
            raise InvariantViolation(
                "Duplicate Grader declarations are not allowed",
                code="DUPLICATE_GRADER_DECLARATION",
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class EvaluationCase(AggregateRoot):
    """Stable identity of an engineering task; owns Prompt and Case Versions."""

    id: CaseId
    project_id: ProjectId
    name: str
    prompt: Prompt
    description: str = ""
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[CaseVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Case name must be non-empty",
                code="INVALID_CASE_NAME",
            )
        self.name = self.name.strip()
        if self.prompt.case_id != self.id:
            raise InvariantViolation(
                "Prompt must belong to its owning Case",
                code="PROMPT_CASE_MISMATCH",
            )

    @classmethod
    def create(
        cls,
        *,
        case_id: CaseId,
        project_id: ProjectId,
        prompt_id: PromptId,
        name: str,
        description: str = "",
    ) -> EvaluationCase:
        return cls(
            id=case_id,
            project_id=project_id,
            name=name,
            description=description,
            prompt=Prompt(id=prompt_id, case_id=case_id),
        )

    @property
    def versions(self) -> tuple[CaseVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> CaseVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: CaseVersionId) -> CaseVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Case version {version_id} not found",
            code="CASE_VERSION_NOT_FOUND",
            details={"case_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: CaseVersionId,
        description: str,
        reference_repository: ReferenceRepositoryState,
        expected_checks: list[str],
        applicable_grader_ids: list[GraderId],
        prompt_version_id: PromptVersionId,
        created_at: datetime | None = None,
    ) -> CaseVersion:
        self._assert_active_identity()
        prompt_version = self.prompt.get_version(prompt_version_id)
        if (
            not prompt_version.is_pinnable()
            and prompt_version.status is not VersionStatus.DRAFT
        ):
            raise InvariantViolation(
                "Case Version must reference a known Prompt Version",
                code="INVALID_PROMPT_VERSION_REF",
            )
        # A draft Case Version may reference a draft Prompt Version authored together.
        if prompt_version.status not in {
            VersionStatus.DRAFT,
            VersionStatus.ACTIVE,
            VersionStatus.SUPERSEDED,
        }:
            raise InvariantViolation(
                "Cannot attach a retired Prompt Version to a Case Version",
                code="INVALID_PROMPT_VERSION_STATUS",
            )
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = CaseVersion(
            id=version_id,
            case_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            description=description,
            reference_repository=reference_repository,
            expected_checks=tuple(expected_checks),
            applicable_grader_ids=tuple(applicable_grader_ids),
            prompt_version_id=prompt_version_id,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: CaseVersionId) -> CaseVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="CaseVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        prompt_version = self.prompt.get_version(draft.prompt_version_id)
        if prompt_version.status is VersionStatus.DRAFT:
            self.prompt.publish_version(prompt_version.id)
        elif not prompt_version.is_pinnable():
            raise InvariantViolation(
                "Published Case Version requires a pinnable Prompt Version",
                code="PROMPT_NOT_PINNABLE",
            )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(
                current,
                CaseVersion(
                    id=current.id,
                    case_id=current.case_id,
                    version_number=current.version_number,
                    status=VersionStatus.SUPERSEDED,
                    description=current.description,
                    reference_repository=current.reference_repository,
                    expected_checks=current.expected_checks,
                    applicable_grader_ids=current.applicable_grader_ids,
                    prompt_version_id=current.prompt_version_id,
                    predecessor_version_id=current.predecessor_version_id,
                    created_at=current.created_at,
                ),
            )
        published = CaseVersion(
            id=draft.id,
            case_id=draft.case_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            description=draft.description,
            reference_repository=draft.reference_repository,
            expected_checks=draft.expected_checks,
            applicable_grader_ids=draft.applicable_grader_ids,
            prompt_version_id=draft.prompt_version_id,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace(draft, published)
        return published

    def deprecate(self) -> None:
        self.status = EntityAdminStatus.DEPRECATED

    def _assert_active_identity(self) -> None:
        if self.status is EntityAdminStatus.DEPRECATED:
            raise InvalidStateTransition(
                "Cannot create versions on a deprecated Case",
                from_state=self.status.value,
                to_state="draft_version",
                entity="EvaluationCase",
            )

    def _replace(self, old: CaseVersion, new: CaseVersion) -> None:
        self._versions[self._versions.index(old)] = new
