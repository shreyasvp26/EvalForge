"""Agent aggregate — Agent identity and Agent Versions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import AdapterId, AgentId, AgentVersionId
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)


@dataclass(frozen=True, slots=True)
class AgentVersion:
    id: AgentVersionId
    agent_id: AgentId
    version_number: VersionNumber
    status: VersionStatus
    label: str
    release_notes: str = ""
    predecessor_version_id: AgentVersionId | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise InvariantViolation(
                "Agent Version label must be non-empty",
                code="INVALID_AGENT_VERSION_LABEL",
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class Agent(AggregateRoot):
    """Stable identity of a coding agent product under evaluation."""

    id: AgentId
    name: str
    adapter_id: AdapterId | None = None
    description: str = ""
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[AgentVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Agent name must be non-empty",
                code="INVALID_AGENT_NAME",
            )
        self.name = self.name.strip()

    @classmethod
    def create(
        cls,
        *,
        agent_id: AgentId,
        name: str,
        description: str = "",
        adapter_id: AdapterId | None = None,
    ) -> Agent:
        return cls(
            id=agent_id,
            name=name,
            description=description,
            adapter_id=adapter_id,
        )

    @property
    def versions(self) -> tuple[AgentVersion, ...]:
        return tuple(self._versions)

    def connect_adapter(self, adapter_id: AdapterId) -> None:
        self.adapter_id = adapter_id

    def active_version(self) -> AgentVersion | None:
        for version in reversed(self._versions):
            if version.status is VersionStatus.ACTIVE:
                return version
        return None

    def get_version(self, version_id: AgentVersionId) -> AgentVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Agent version {version_id} not found",
            code="AGENT_VERSION_NOT_FOUND",
            details={"agent_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: AgentVersionId,
        label: str,
        release_notes: str = "",
        created_at: datetime | None = None,
    ) -> AgentVersion:
        predecessor = self.active_version()
        version_number = (
            VersionNumber(1)
            if predecessor is None
            else predecessor.version_number.next()
        )
        version = AgentVersion(
            id=version_id,
            agent_id=self.id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            label=label,
            release_notes=release_notes,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: AgentVersionId) -> AgentVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="AgentVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(
                current,
                AgentVersion(
                    id=current.id,
                    agent_id=current.agent_id,
                    version_number=current.version_number,
                    status=VersionStatus.SUPERSEDED,
                    label=current.label,
                    release_notes=current.release_notes,
                    predecessor_version_id=current.predecessor_version_id,
                    created_at=current.created_at,
                ),
            )
        published = AgentVersion(
            id=draft.id,
            agent_id=draft.agent_id,
            version_number=draft.version_number,
            status=VersionStatus.ACTIVE,
            label=draft.label,
            release_notes=draft.release_notes,
            predecessor_version_id=draft.predecessor_version_id,
            created_at=draft.created_at,
        )
        self._replace(draft, published)
        return published

    def can_be_targeted_by_run(self) -> bool:
        return (
            self.status is EntityAdminStatus.ACTIVE
            and self.adapter_id is not None
            and self.active_version() is not None
        )

    def _replace(self, old: AgentVersion, new: AgentVersion) -> None:
        self._versions[self._versions.index(old)] = new
