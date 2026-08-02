"""Adapter ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.agent_integration.adapter import Adapter, AdapterVersion
from agent_eval_domain.common.ids import AdapterId, AdapterVersionId, AgentId

from agent_eval_infrastructure.database.models.agent_integration.adapter import (
    AdapterOrm,
    AdapterVersionOrm,
)
from agent_eval_infrastructure.mappers.common import (
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def adapter_version_to_domain(row: AdapterVersionOrm) -> AdapterVersion:
    return AdapterVersion(
        id=AdapterVersionId(row.id),
        adapter_id=AdapterId(row.adapter_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        label=row.label,
        notes=row.notes,
        predecessor_version_id=(
            AdapterVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def adapter_to_domain(row: AdapterOrm, versions: list[AdapterVersionOrm]) -> Adapter:
    mapped = [
        adapter_version_to_domain(v)
        for v in sorted(versions, key=lambda item: item.version_number)
    ]
    return Adapter(
        id=AdapterId(row.id),
        agent_id=AgentId(row.agent_id),
        name=row.name,
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        _versions=mapped,
    )


def adapter_to_orm(adapter: Adapter, row: AdapterOrm | None = None) -> AdapterOrm:
    target = row or AdapterOrm(id=adapter.id.value)
    target.id = adapter.id.value
    target.agent_id = adapter.agent_id.value
    target.name = adapter.name
    target.status = adapter.status.value
    target.created_at = adapter.created_at
    return target


def adapter_version_to_orm(version: AdapterVersion) -> AdapterVersionOrm:
    return AdapterVersionOrm(
        id=version.id.value,
        adapter_id=version.adapter_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        label=version.label,
        notes=version.notes,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )
