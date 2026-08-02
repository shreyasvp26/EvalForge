"""SQLAlchemy GraderRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import GraderId
from agent_eval_domain.grading.grader import Grader
from sqlalchemy import select

from agent_eval_infrastructure.database.models.grading.grader import (
    GraderOrm,
    GraderVersionOrm,
)
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.mappers.grader import (
    grader_to_domain,
    grader_to_orm,
    grader_version_to_orm,
)
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyGraderRepository(SqlAlchemyRepository):
    def get(self, grader_id: GraderId) -> Grader:
        row = self.session.get(GraderOrm, grader_id.value)
        require_found(row, entity_type="Grader", entity_id=grader_id.value)
        return self._load_grader(row)  # type: ignore[arg-type]

    def save(self, grader: Grader) -> None:
        row = self.session.get(GraderOrm, grader.id.value)
        mapped = grader_to_orm(grader, row)
        if row is None:
            self.session.add(mapped)

        for version in grader.versions:
            version_row = self.session.get(GraderVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(grader_version_to_orm(version))
            else:
                version_row.status = version.status.value

    def _load_grader(self, row: GraderOrm) -> Grader:
        versions = list(
            self.session.scalars(
                select(GraderVersionOrm).where(GraderVersionOrm.grader_id == row.id)
            )
        )
        return grader_to_domain(row, versions)
