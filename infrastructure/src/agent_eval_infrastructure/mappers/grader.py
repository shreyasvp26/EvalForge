"""Grader ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.common.ids import GraderId, GraderVersionId
from agent_eval_domain.grading.grader import Grader, GraderFamily, GraderVersion

from agent_eval_infrastructure.database.models.grading.grader import (
    GraderOrm,
    GraderVersionOrm,
)
from agent_eval_infrastructure.mappers.common import (
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def grader_version_to_domain(row: GraderVersionOrm) -> GraderVersion:
    return GraderVersion(
        id=GraderVersionId(row.id),
        grader_id=GraderId(row.grader_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        label=row.label,
        specification=row.specification,
        predecessor_version_id=(
            GraderVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def grader_to_domain(row: GraderOrm, versions: list[GraderVersionOrm]) -> Grader:
    mapped = [
        grader_version_to_domain(v)
        for v in sorted(versions, key=lambda item: item.version_number)
    ]
    return Grader(
        id=GraderId(row.id),
        name=row.name,
        family=GraderFamily(row.family),
        description=row.description,
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        _versions=mapped,
    )


def grader_to_orm(grader: Grader, row: GraderOrm | None = None) -> GraderOrm:
    target = row or GraderOrm(id=grader.id.value)
    target.id = grader.id.value
    target.name = grader.name
    target.family = grader.family.value
    target.description = grader.description
    target.status = grader.status.value
    target.created_at = grader.created_at
    return target


def grader_version_to_orm(version: GraderVersion) -> GraderVersionOrm:
    return GraderVersionOrm(
        id=version.id.value,
        grader_id=version.grader_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        label=version.label,
        specification=version.specification,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )
