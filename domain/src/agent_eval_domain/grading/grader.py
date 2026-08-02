"""Grader aggregate — Grader identity and Grader Versions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import GraderId, GraderVersionId
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)


class GraderFamily(StrEnum):
    """Both families are modeled identically at the domain level."""

    OBJECTIVE = "objective"
    RUBRIC = "rubric"


@dataclass(frozen=True, slots=True)
class GraderVersion:
    id: GraderVersionId
    grader_id: GraderId
    version_number: VersionNumber
    status: VersionStatus
    label: str
    specification: str
    predecessor_version_id: GraderVersionId | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise InvariantViolation(
                "Grader Version label must be non-empty",
                code="INVALID_GRADER_VERSION_LABEL",
            )
        if not self.specification.strip():
            raise InvariantViolation(
                "Grader Version specification must be non-empty",
                code="INVALID_GRADER_SPECIFICATION",
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class Grader(AggregateRoot):
    """Independently invokable grading capability. Never modifies Runs."""

    id: GraderId
    name: str
    family: GraderFamily
    description: str = ""
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[GraderVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Grader name must be non-empty",
                code="INVALID_GRADER_NAME",
            )
        self.name = self.name.strip()

    @classmethod
    def create(
        cls,
        *,
        grader_id: GraderId,
        name: str,
        family: GraderFamily,
        description: str = "",
    ) -> Grader:
        return cls(
            id=grader_id,
            name=name,
            family=family,
            description=description,
        )

    @property
    def versions(self) -> tuple[GraderVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> GraderVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: GraderVersionId) -> GraderVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Grader version {version_id} not found",
            code="GRADER_VERSION_NOT_FOUND",
            details={"grader_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: GraderVersionId,
        label: str,
        specification: str,
        created_at: datetime | None = None,
    ) -> GraderVersion:
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = GraderVersion(
            id=version_id,
            grader_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            label=label,
            specification=specification,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: GraderVersionId) -> GraderVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="GraderVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(
                current,
                GraderVersion(
                    id=current.id,
                    grader_id=current.grader_id,
                    version_number=current.version_number,
                    status=VersionStatus.SUPERSEDED,
                    label=current.label,
                    specification=current.specification,
                    predecessor_version_id=current.predecessor_version_id,
                    created_at=current.created_at,
                ),
            )
        published = GraderVersion(
            id=draft.id,
            grader_id=draft.grader_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            label=draft.label,
            specification=draft.specification,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace(draft, published)
        return published

    def _replace(self, old: GraderVersion, new: GraderVersion) -> None:
        self._versions[self._versions.index(old)] = new
