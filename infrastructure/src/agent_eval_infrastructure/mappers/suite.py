"""Suite ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.common.ids import (
    CaseVersionId,
    ProjectId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
    SuiteVersion,
)

from agent_eval_infrastructure.database.models.associations.suite_composition import (
    SuiteCompositionOrm,
)
from agent_eval_infrastructure.database.models.evaluation_management.suite import (
    SuiteOrm,
    SuiteVersionOrm,
)
from agent_eval_infrastructure.mappers.common import (
    deterministic_id,
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def suite_composition_to_domain(row: SuiteCompositionOrm) -> SuiteCompositionEntry:
    return SuiteCompositionEntry(
        case_version_id=CaseVersionId(row.case_version_id),
        position=row.position,
        case_project_id=ProjectId(row.case_project_id),
    )


def suite_version_to_domain(
    row: SuiteVersionOrm,
    compositions: list[SuiteCompositionOrm],
) -> SuiteVersion:
    entries = tuple(
        sorted(
            (suite_composition_to_domain(c) for c in compositions),
            key=lambda e: e.position,
        )
    )
    return SuiteVersion(
        id=SuiteVersionId(row.id),
        suite_id=SuiteId(row.suite_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        composition=entries,
        predecessor_version_id=(
            SuiteVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def suite_to_domain(
    row: SuiteOrm,
    version_rows: list[SuiteVersionOrm],
    compositions_by_version: dict[str, list[SuiteCompositionOrm]],
) -> EvaluationSuite:
    versions = [
        suite_version_to_domain(v, compositions_by_version.get(v.id, []))
        for v in sorted(version_rows, key=lambda item: item.version_number)
    ]
    return EvaluationSuite(
        id=SuiteId(row.id),
        project_id=ProjectId(row.project_id),
        name=row.name,
        description=row.description,
        catalog_key=getattr(row, "catalog_key", "") or "",
        catalog_visible=bool(getattr(row, "catalog_visible", False)),
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        _versions=versions,
    )


def suite_to_orm(suite: EvaluationSuite, row: SuiteOrm | None = None) -> SuiteOrm:
    target = row or SuiteOrm(id=suite.id.value)
    target.id = suite.id.value
    target.project_id = suite.project_id.value
    target.name = suite.name
    target.description = suite.description
    target.catalog_key = suite.catalog_key
    target.catalog_visible = suite.catalog_visible
    target.status = suite.status.value
    target.created_at = suite.created_at
    return target


def suite_version_to_orm(version: SuiteVersion) -> SuiteVersionOrm:
    return SuiteVersionOrm(
        id=version.id.value,
        suite_id=version.suite_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )


def suite_composition_to_orm(
    version: SuiteVersion,
    entry: SuiteCompositionEntry,
) -> SuiteCompositionOrm:
    return SuiteCompositionOrm(
        id=deterministic_id(version.id.value, entry.case_version_id.value),
        suite_version_id=version.id.value,
        case_version_id=entry.case_version_id.value,
        case_project_id=entry.case_project_id.value,
        position=entry.position,
        created_at=version.created_at,
    )
