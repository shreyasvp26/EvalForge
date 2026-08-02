"""SQLAlchemy ProjectRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.evaluation_management.project import Project

from agent_eval_infrastructure.database.models.evaluation_management.project import (
    ProjectOrm,
)
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.mappers.project import project_to_domain, project_to_orm
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyProjectRepository(SqlAlchemyRepository):
    def get(self, project_id: ProjectId) -> Project:
        row = self.session.get(ProjectOrm, project_id.value)
        return project_to_domain(
            require_found(row, entity_type="Project", entity_id=project_id.value)
        )

    def save(self, project: Project) -> None:
        row = self.session.get(ProjectOrm, project.id.value)
        mapped = project_to_orm(project, row)
        if row is None:
            self.session.add(mapped)

    def list_all(self) -> list[Project]:
        from sqlalchemy import select

        rows = list(self.session.scalars(select(ProjectOrm)))
        return [project_to_domain(row) for row in rows]
