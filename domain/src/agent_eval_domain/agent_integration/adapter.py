"""Adapter identity and Adapter Versions — pure translation boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import AdapterId, AdapterVersionId, AgentId
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)


@dataclass(frozen=True, slots=True)
class AdapterVersion:
    id: AdapterVersionId
    adapter_id: AdapterId
    version_number: VersionNumber
    status: VersionStatus
    label: str
    notes: str = ""
    predecessor_version_id: AdapterVersionId | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise InvariantViolation(
                "Adapter Version label must be non-empty",
                code="INVALID_ADAPTER_VERSION_LABEL",
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class Adapter(AggregateRoot):
    """Vendor-specific translation identity connected to exactly one Agent.

    Adapters never persist business state (Invariant 7) — this entity only
    records identity and version lineage for pinning on Runs.
    """

    id: AdapterId
    agent_id: AgentId
    name: str
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[AdapterVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Adapter name must be non-empty",
                code="INVALID_ADAPTER_NAME",
            )
        self.name = self.name.strip()

    @classmethod
    def create(
        cls,
        *,
        adapter_id: AdapterId,
        agent_id: AgentId,
        name: str,
    ) -> Adapter:
        return cls(id=adapter_id, agent_id=agent_id, name=name)

    @property
    def versions(self) -> tuple[AdapterVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> AdapterVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: AdapterVersionId) -> AdapterVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Adapter version {version_id} not found",
            code="ADAPTER_VERSION_NOT_FOUND",
            details={"adapter_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: AdapterVersionId,
        label: str,
        notes: str = "",
        created_at: datetime | None = None,
    ) -> AdapterVersion:
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = AdapterVersion(
            id=version_id,
            adapter_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            label=label,
            notes=notes,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: AdapterVersionId) -> AdapterVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="AdapterVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(
                current,
                AdapterVersion(
                    id=current.id,
                    adapter_id=current.adapter_id,
                    version_number=current.version_number,
                    status=VersionStatus.SUPERSEDED,
                    label=current.label,
                    notes=current.notes,
                    predecessor_version_id=current.predecessor_version_id,
                    created_at=current.created_at,
                ),
            )
        published = AdapterVersion(
            id=draft.id,
            adapter_id=draft.adapter_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            label=draft.label,
            notes=draft.notes,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace(draft, published)
        return published

    def _replace(self, old: AdapterVersion, new: AdapterVersion) -> None:
        self._versions[self._versions.index(old)] = new
