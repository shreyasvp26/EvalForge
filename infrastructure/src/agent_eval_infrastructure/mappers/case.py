"""Case / Prompt ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.common.ids import (
    CaseId,
    CaseVersionId,
    GraderId,
    ProjectId,
    PromptId,
    PromptVersionId,
)
from agent_eval_domain.evaluation_management.case import (
    CaseVersion,
    EvaluationCase,
    Prompt,
    PromptVersion,
    ReferenceRepositoryState,
)

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
from agent_eval_infrastructure.mappers.common import (
    deterministic_id,
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def prompt_version_to_domain(row: PromptVersionOrm) -> PromptVersion:
    return PromptVersion(
        id=PromptVersionId(row.id),
        prompt_id=PromptId(row.prompt_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        content=row.content,
        predecessor_version_id=(
            PromptVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def prompt_to_domain(
    row: PromptOrm,
    version_rows: list[PromptVersionOrm],
) -> Prompt:
    versions = [
        prompt_version_to_domain(v)
        for v in sorted(version_rows, key=lambda item: item.version_number)
    ]
    prompt = Prompt(
        id=PromptId(row.id),
        case_id=CaseId(row.case_id),
        created_at=row.created_at,
    )
    prompt._versions = versions  # noqa: SLF001 — rehydration
    return prompt


def case_version_to_domain(
    row: CaseVersionOrm,
    grader_ids: list[str],
) -> CaseVersion:
    return CaseVersion(
        id=CaseVersionId(row.id),
        case_id=CaseId(row.case_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        description=row.description,
        reference_repository=ReferenceRepositoryState(
            repository_url=row.repository_url,
            commit_sha=row.commit_sha,
            subdirectory=row.subdirectory,
        ),
        expected_checks=tuple(str(x) for x in list(row.expected_checks or [])),
        applicable_grader_ids=tuple(GraderId(g) for g in grader_ids),
        prompt_version_id=PromptVersionId(row.prompt_version_id),
        predecessor_version_id=(
            CaseVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def case_to_domain(
    case_row: CaseOrm,
    prompt_row: PromptOrm,
    prompt_versions: list[PromptVersionOrm],
    case_versions: list[CaseVersionOrm],
    declarations_by_version: dict[str, list[CaseGraderDeclarationOrm]],
) -> EvaluationCase:
    prompt = prompt_to_domain(prompt_row, prompt_versions)
    versions = [
        case_version_to_domain(
            v,
            [d.grader_id for d in declarations_by_version.get(v.id, [])],
        )
        for v in sorted(case_versions, key=lambda item: item.version_number)
    ]
    return EvaluationCase(
        id=CaseId(case_row.id),
        project_id=ProjectId(case_row.project_id),
        name=case_row.name,
        prompt=prompt,
        description=case_row.description,
        status=parse_admin_status(case_row.status),
        created_at=case_row.created_at,
        _versions=versions,
    )


def case_to_orm(case: EvaluationCase, row: CaseOrm | None = None) -> CaseOrm:
    target = row or CaseOrm(id=case.id.value)
    target.id = case.id.value
    target.project_id = case.project_id.value
    target.name = case.name
    target.description = case.description
    target.status = case.status.value
    target.created_at = case.created_at
    return target


def prompt_to_orm(prompt: Prompt) -> PromptOrm:
    return PromptOrm(
        id=prompt.id.value,
        case_id=prompt.case_id.value,
        created_at=prompt.created_at,
    )


def prompt_version_to_orm(version: PromptVersion) -> PromptVersionOrm:
    return PromptVersionOrm(
        id=version.id.value,
        prompt_id=version.prompt_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        content=version.content,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )


def case_version_to_orm(version: CaseVersion) -> CaseVersionOrm:
    return CaseVersionOrm(
        id=version.id.value,
        case_id=version.case_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        description=version.description,
        repository_url=version.reference_repository.repository_url,
        commit_sha=version.reference_repository.commit_sha,
        subdirectory=version.reference_repository.subdirectory,
        expected_checks=list(version.expected_checks),
        prompt_version_id=version.prompt_version_id.value,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )


def case_grader_declaration_to_orm(
    version: CaseVersion,
    grader_id: GraderId,
) -> CaseGraderDeclarationOrm:
    return CaseGraderDeclarationOrm(
        id=deterministic_id(version.id.value, grader_id.value),
        case_version_id=version.id.value,
        grader_id=grader_id.value,
        created_at=version.created_at,
    )
