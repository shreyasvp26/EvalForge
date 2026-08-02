"""Project DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.evaluation_management.project import Project


@dataclass(frozen=True, slots=True)
class ProjectDTO:
    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    settings: dict[str, str]

    @classmethod
    def from_domain(cls, project: Project) -> ProjectDTO:
        return cls(
            id=project.id.value,
            name=project.name,
            description=project.description,
            status=project.status.value,
            created_at=project.created_at,
            settings=dict(project.settings),
        )
