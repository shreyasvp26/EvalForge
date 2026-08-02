"""Project — top-level authorization and organizational scoping boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.versioning.status import EntityAdminStatus


@dataclass(slots=True)
class Project(AggregateRoot):
    """Top-level scoping boundary for Suites, Cases, and Runs."""

    id: ProjectId
    name: str
    description: str = ""
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    settings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Project name must be non-empty",
                code="INVALID_PROJECT_NAME",
            )
        object.__setattr__(self, "name", self.name.strip())

    @classmethod
    def create(
        cls,
        *,
        project_id: ProjectId,
        name: str,
        description: str = "",
        settings: dict[str, str] | None = None,
    ) -> Project:
        return cls(
            id=project_id,
            name=name,
            description=description,
            settings=dict(settings or {}),
        )

    def rename(self, name: str) -> None:
        if not name.strip():
            raise InvariantViolation(
                "Project name must be non-empty",
                code="INVALID_PROJECT_NAME",
            )
        self.name = name.strip()

    def update_settings(self, settings: dict[str, str]) -> None:
        self.settings = dict(settings)

    def deprecate(self) -> None:
        self.status = EntityAdminStatus.DEPRECATED

    def is_active(self) -> bool:
        return self.status is EntityAdminStatus.ACTIVE
