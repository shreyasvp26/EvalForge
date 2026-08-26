"""Platform catalog ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.common.ids import PlatformId, PlatformVersionId
from agent_eval_domain.platform.platform import Platform, PlatformVersion

from agent_eval_infrastructure.database.models.platform import (
    PlatformOrm,
    PlatformVersionOrm,
)
from agent_eval_infrastructure.mappers.common import (
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def platform_version_to_domain(row: PlatformVersionOrm) -> PlatformVersion:
    return PlatformVersion(
        id=PlatformVersionId(row.id),
        platform_id=PlatformId(row.platform_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        label=row.label,
        sandbox_policy=dict(row.sandbox_policy),
        execution_policy=dict(row.execution_policy),
        timeout_policy=dict(row.timeout_policy),
        environment_policy=dict(row.environment_policy),
        grading_policy=dict(row.grading_policy),
        notes=row.notes,
        predecessor_version_id=(
            PlatformVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def platform_to_domain(
    row: PlatformOrm, versions: list[PlatformVersionOrm]
) -> Platform:
    return Platform(
        id=PlatformId(row.id),
        name=row.name,
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        _versions=[
            platform_version_to_domain(version)
            for version in sorted(versions, key=lambda item: item.version_number)
        ],
    )


def platform_to_orm(platform: Platform, row: PlatformOrm | None = None) -> PlatformOrm:
    target = row or PlatformOrm(id=platform.id.value)
    target.id = platform.id.value
    target.name = platform.name
    target.status = platform.status.value
    target.created_at = platform.created_at
    return target


def platform_version_to_orm(version: PlatformVersion) -> PlatformVersionOrm:
    return PlatformVersionOrm(
        id=version.id.value,
        platform_id=version.platform_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        label=version.label,
        sandbox_policy=dict(version.sandbox_policy),
        execution_policy=dict(version.execution_policy),
        timeout_policy=dict(version.timeout_policy),
        environment_policy=dict(version.environment_policy),
        grading_policy=dict(version.grading_policy),
        notes=version.notes,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )
