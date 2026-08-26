"""Evaluation Suite aggregate — owns Suite Versions and composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvalidStateTransition, InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import (
    CaseVersionId,
    ProjectId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)


@dataclass(frozen=True, slots=True)
class SuiteCompositionEntry:
    """Ordered Case Version membership within a Suite Version."""

    case_version_id: CaseVersionId
    position: int
    case_project_id: ProjectId

    def __post_init__(self) -> None:
        if self.position < 0:
            raise InvariantViolation(
                "Suite composition position must be >= 0",
                code="INVALID_COMPOSITION_POSITION",
            )


@dataclass(frozen=True, slots=True)
class SuiteVersion:
    """Immutable point-in-time Suite composition."""

    id: SuiteVersionId
    suite_id: SuiteId
    version_number: VersionNumber
    status: VersionStatus
    composition: tuple[SuiteCompositionEntry, ...]
    predecessor_version_id: SuiteVersionId | None
    created_at: datetime

    def case_version_ids(self) -> tuple[CaseVersionId, ...]:
        return tuple(entry.case_version_id for entry in self.composition)

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class EvaluationSuite(AggregateRoot):
    """Stable identity of a named collection of Cases.

    Published SuiteVersions are the product's immutable benchmarks. Catalog
    fields make discoverable suites answer \"what benchmark can I run?\".
    """

    id: SuiteId
    project_id: ProjectId
    name: str
    description: str = ""
    catalog_key: str = ""
    catalog_visible: bool = False
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[SuiteVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Suite name must be non-empty",
                code="INVALID_SUITE_NAME",
            )
        self.name = self.name.strip()
        self.catalog_key = self.catalog_key.strip()

    @classmethod
    def create(
        cls,
        *,
        suite_id: SuiteId,
        project_id: ProjectId,
        name: str,
        description: str = "",
        catalog_key: str = "",
        catalog_visible: bool = False,
    ) -> EvaluationSuite:
        return cls(
            id=suite_id,
            project_id=project_id,
            name=name,
            description=description,
            catalog_key=catalog_key,
            catalog_visible=catalog_visible,
        )

    def set_catalog(
        self,
        *,
        catalog_key: str | None = None,
        catalog_visible: bool | None = None,
    ) -> None:
        """Update catalog discovery fields (identity-level, not version history)."""
        if catalog_key is not None:
            self.catalog_key = catalog_key.strip()
        if catalog_visible is not None:
            self.catalog_visible = catalog_visible

    @property
    def versions(self) -> tuple[SuiteVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> SuiteVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: SuiteVersionId) -> SuiteVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Suite version {version_id} not found on suite {self.id}",
            code="SUITE_VERSION_NOT_FOUND",
            details={"suite_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: SuiteVersionId,
        composition: list[SuiteCompositionEntry],
        created_at: datetime | None = None,
    ) -> SuiteVersion:
        self._assert_active_identity()
        self._validate_composition(composition)
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = SuiteVersion(
            id=version_id,
            suite_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            composition=tuple(sorted(composition, key=lambda entry: entry.position)),
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: SuiteVersionId) -> SuiteVersion:
        """Activate a draft; supersede the previously active version."""
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="SuiteVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current_active = self.active_version()
        if current_active is not None and current_active.id != draft.id:
            self._replace_version(
                current_active,
                SuiteVersion(
                    id=current_active.id,
                    suite_id=current_active.suite_id,
                    version_number=current_active.version_number,
                    status=VersionStatus.SUPERSEDED,
                    composition=current_active.composition,
                    predecessor_version_id=current_active.predecessor_version_id,
                    created_at=current_active.created_at,
                ),
            )
        published = SuiteVersion(
            id=draft.id,
            suite_id=draft.suite_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            composition=draft.composition,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace_version(draft, published)
        return published

    def retire_version(self, version_id: SuiteVersionId) -> SuiteVersion:
        version = self.get_version(version_id)
        assert_version_transition(
            entity="SuiteVersion",
            current=version.status,
            target=VersionStatus.RETIRED,
        )
        retired = SuiteVersion(
            id=version.id,
            suite_id=version.suite_id,
            version_number=version.version_number,
            status=VersionStatus.RETIRED,
            composition=version.composition,
            predecessor_version_id=version.predecessor_version_id,
            created_at=version.created_at,
        )
        self._replace_version(version, retired)
        return retired

    def deprecate(self) -> None:
        self.status = EntityAdminStatus.DEPRECATED

    def _assert_active_identity(self) -> None:
        if self.status is EntityAdminStatus.DEPRECATED:
            raise InvalidStateTransition(
                "Cannot create versions on a deprecated Suite",
                from_state=self.status.value,
                to_state="draft_version",
                entity="EvaluationSuite",
            )

    def _validate_composition(self, composition: list[SuiteCompositionEntry]) -> None:
        if not composition:
            raise InvariantViolation(
                "Suite Version composition must include at least one Case Version",
                code="EMPTY_SUITE_COMPOSITION",
            )
        positions = [entry.position for entry in composition]
        if len(positions) != len(set(positions)):
            raise InvariantViolation(
                "Suite composition positions must be unique",
                code="DUPLICATE_COMPOSITION_POSITION",
            )
        case_ids = [entry.case_version_id for entry in composition]
        if len(case_ids) != len(set(case_ids)):
            raise InvariantViolation(
                "A Case Version may appear at most once in a Suite Version",
                code="DUPLICATE_CASE_IN_SUITE",
            )
        for entry in composition:
            if entry.case_project_id != self.project_id:
                raise InvariantViolation(
                    "Suite composition cannot cross Project boundaries",
                    code="CROSS_PROJECT_COMPOSITION",
                    details={
                        "suite_project_id": self.project_id.value,
                        "case_project_id": entry.case_project_id.value,
                        "case_version_id": entry.case_version_id.value,
                    },
                )

    def _replace_version(self, old: SuiteVersion, new: SuiteVersion) -> None:
        index = self._versions.index(old)
        self._versions[index] = new
