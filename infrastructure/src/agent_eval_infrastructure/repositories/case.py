"""SQLAlchemy CaseRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import CaseId, CaseVersionId, ProjectId
from agent_eval_domain.evaluation_management.case import CaseVersion, EvaluationCase
from sqlalchemy import select

from agent_eval_infrastructure.database.models.associations.case_grader import (
    CaseGraderDeclarationOrm,
)
from agent_eval_infrastructure.database.models.evaluation_management.case import (
    CaseOrm,
    CaseVersionOrm,
)
from agent_eval_infrastructure.database.models.evaluation_management.prompt import (
    PromptOrm,
    PromptVersionOrm,
)
from agent_eval_infrastructure.mappers.case import (
    case_grader_declaration_to_orm,
    case_to_domain,
    case_to_orm,
    case_version_to_domain,
    case_version_to_orm,
    prompt_to_orm,
    prompt_version_to_orm,
)
from agent_eval_infrastructure.mappers.common import deterministic_id, require_found
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyCaseRepository(SqlAlchemyRepository):
    def get(self, case_id: CaseId) -> EvaluationCase:
        row = self.session.get(CaseOrm, case_id.value)
        require_found(row, entity_type="Case", entity_id=case_id.value)
        return self._load_case(row)  # type: ignore[arg-type]

    def get_version(self, case_version_id: CaseVersionId) -> CaseVersion:
        row = self.session.get(CaseVersionOrm, case_version_id.value)
        require_found(row, entity_type="CaseVersion", entity_id=case_version_id.value)
        declarations = list(
            self.session.scalars(
                select(CaseGraderDeclarationOrm).where(
                    CaseGraderDeclarationOrm.case_version_id == case_version_id.value
                )
            )
        )
        return case_version_to_domain(
            row,  # type: ignore[arg-type]
            [d.grader_id for d in declarations],
        )

    def save(self, case: EvaluationCase) -> None:
        row = self.session.get(CaseOrm, case.id.value)
        mapped = case_to_orm(case, row)
        if row is None:
            self.session.add(mapped)

        prompt_row = self.session.get(PromptOrm, case.prompt.id.value)
        if prompt_row is None:
            self.session.add(prompt_to_orm(case.prompt))

        for prompt_version in case.prompt.versions:
            pv_row = self.session.get(PromptVersionOrm, prompt_version.id.value)
            if pv_row is None:
                self.session.add(prompt_version_to_orm(prompt_version))
            else:
                pv_row.status = prompt_version.status.value

        for version in case.versions:
            version_row = self.session.get(CaseVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(case_version_to_orm(version))
            else:
                version_row.status = version.status.value

            for grader_id in version.applicable_grader_ids:
                declaration_id = deterministic_id(version.id.value, grader_id.value)
                if self.session.get(CaseGraderDeclarationOrm, declaration_id) is None:
                    self.session.add(case_grader_declaration_to_orm(version, grader_id))

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationCase]:
        rows = list(
            self.session.scalars(
                select(CaseOrm)
                .where(CaseOrm.project_id == project_id.value)
                .order_by(CaseOrm.name)
            )
        )
        return [self._load_case(row) for row in rows]

    def _load_case(self, row: CaseOrm) -> EvaluationCase:
        prompt_row = self.session.scalars(
            select(PromptOrm).where(PromptOrm.case_id == row.id)
        ).one()
        prompt_versions = list(
            self.session.scalars(
                select(PromptVersionOrm).where(
                    PromptVersionOrm.prompt_id == prompt_row.id
                )
            )
        )
        case_versions = list(
            self.session.scalars(
                select(CaseVersionOrm).where(CaseVersionOrm.case_id == row.id)
            )
        )
        version_ids = [v.id for v in case_versions]
        declarations_by_version: dict[str, list[CaseGraderDeclarationOrm]] = {
            vid: [] for vid in version_ids
        }
        if version_ids:
            declarations = list(
                self.session.scalars(
                    select(CaseGraderDeclarationOrm).where(
                        CaseGraderDeclarationOrm.case_version_id.in_(version_ids)
                    )
                )
            )
            for declaration in declarations:
                declarations_by_version.setdefault(
                    declaration.case_version_id, []
                ).append(declaration)
        return case_to_domain(
            row,
            prompt_row,
            prompt_versions,
            case_versions,
            declarations_by_version,
        )
