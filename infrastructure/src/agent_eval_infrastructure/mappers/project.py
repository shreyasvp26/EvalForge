"""Project ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.evaluation_management.project import Project

from agent_eval_infrastructure.database.models.evaluation_management.project import (
    ProjectOrm,
)
from agent_eval_infrastructure.mappers.common import parse_admin_status


def project_to_domain(row: ProjectOrm) -> Project:
    return Project(
        id=ProjectId(row.id),
        name=row.name,
        description=row.description,
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        settings={str(k): str(v) for k, v in dict(row.settings or {}).items()},
    )


def project_to_orm(project: Project, row: ProjectOrm | None = None) -> ProjectOrm:
    target = row or ProjectOrm(id=project.id.value)
    target.id = project.id.value
    target.name = project.name
    target.description = project.description
    target.status = project.status.value
    target.created_at = project.created_at
    target.settings = dict(project.settings)
    return target
