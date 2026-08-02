"""SQLAlchemy SuiteRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import ProjectId, SuiteId, SuiteVersionId
from agent_eval_domain.evaluation_management.suite import EvaluationSuite, SuiteVersion
from sqlalchemy import select

from agent_eval_infrastructure.database.models.associations.suite_composition import (
    SuiteCompositionOrm,
)
from agent_eval_infrastructure.database.models.evaluation_management.suite import (
    SuiteOrm,
    SuiteVersionOrm,
)
from agent_eval_infrastructure.mappers.common import deterministic_id, require_found
from agent_eval_infrastructure.mappers.suite import (
    suite_composition_to_orm,
    suite_to_domain,
    suite_to_orm,
    suite_version_to_domain,
    suite_version_to_orm,
)
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemySuiteRepository(SqlAlchemyRepository):
    def get(self, suite_id: SuiteId) -> EvaluationSuite:
        row = self.session.get(SuiteOrm, suite_id.value)
        require_found(row, entity_type="Suite", entity_id=suite_id.value)
        return self._load_suite(row)  # type: ignore[arg-type]

    def get_version(self, suite_version_id: SuiteVersionId) -> SuiteVersion:
        row = self.session.get(SuiteVersionOrm, suite_version_id.value)
        require_found(row, entity_type="SuiteVersion", entity_id=suite_version_id.value)
        compositions = list(
            self.session.scalars(
                select(SuiteCompositionOrm).where(
                    SuiteCompositionOrm.suite_version_id == suite_version_id.value
                )
            )
        )
        return suite_version_to_domain(row, compositions)  # type: ignore[arg-type]

    def save(self, suite: EvaluationSuite) -> None:
        row = self.session.get(SuiteOrm, suite.id.value)
        mapped = suite_to_orm(suite, row)
        if row is None:
            self.session.add(mapped)

        for version in suite.versions:
            version_row = self.session.get(SuiteVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(suite_version_to_orm(version))
            else:
                # Lifecycle status may advance; content fields remain insert-once.
                version_row.status = version.status.value

            for entry in version.composition:
                composition_id = deterministic_id(
                    version.id.value, entry.case_version_id.value
                )
                if self.session.get(SuiteCompositionOrm, composition_id) is None:
                    self.session.add(suite_composition_to_orm(version, entry))

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationSuite]:
        rows = list(
            self.session.scalars(
                select(SuiteOrm)
                .where(SuiteOrm.project_id == project_id.value)
                .order_by(SuiteOrm.name)
            )
        )
        return [self._load_suite(row) for row in rows]

    def _load_suite(self, row: SuiteOrm) -> EvaluationSuite:
        versions = list(
            self.session.scalars(
                select(SuiteVersionOrm).where(SuiteVersionOrm.suite_id == row.id)
            )
        )
        version_ids = [v.id for v in versions]
        compositions_by_version: dict[str, list[SuiteCompositionOrm]] = {
            vid: [] for vid in version_ids
        }
        if version_ids:
            composition_rows = list(
                self.session.scalars(
                    select(SuiteCompositionOrm).where(
                        SuiteCompositionOrm.suite_version_id.in_(version_ids)
                    )
                )
            )
            for composition in composition_rows:
                compositions_by_version.setdefault(
                    composition.suite_version_id, []
                ).append(composition)
        return suite_to_domain(row, versions, compositions_by_version)
