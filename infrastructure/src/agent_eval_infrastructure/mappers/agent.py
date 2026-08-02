"""Agent ORM ↔ Domain mapping."""

from __future__ import annotations

from agent_eval_domain.agent_integration.agent import Agent, AgentVersion
from agent_eval_domain.common.ids import AdapterId, AgentId, AgentVersionId

from agent_eval_infrastructure.database.models.agent_integration.agent import (
    AgentOrm,
    AgentVersionOrm,
)
from agent_eval_infrastructure.mappers.common import (
    parse_admin_status,
    parse_version_number,
    parse_version_status,
)


def agent_version_to_domain(row: AgentVersionOrm) -> AgentVersion:
    return AgentVersion(
        id=AgentVersionId(row.id),
        agent_id=AgentId(row.agent_id),
        version_number=parse_version_number(row.version_number),
        status=parse_version_status(row.status),
        label=row.label,
        release_notes=row.release_notes,
        predecessor_version_id=(
            AgentVersionId(row.predecessor_version_id)
            if row.predecessor_version_id
            else None
        ),
        created_at=row.created_at,
    )


def agent_to_domain(row: AgentOrm, versions: list[AgentVersionOrm]) -> Agent:
    mapped = [
        agent_version_to_domain(v)
        for v in sorted(versions, key=lambda item: item.version_number)
    ]
    return Agent(
        id=AgentId(row.id),
        name=row.name,
        description=row.description,
        adapter_id=AdapterId(row.adapter_id) if row.adapter_id else None,
        status=parse_admin_status(row.status),
        created_at=row.created_at,
        _versions=mapped,
    )


def agent_to_orm(agent: Agent, row: AgentOrm | None = None) -> AgentOrm:
    target = row or AgentOrm(id=agent.id.value)
    target.id = agent.id.value
    target.name = agent.name
    target.description = agent.description
    target.status = agent.status.value
    target.adapter_id = agent.adapter_id.value if agent.adapter_id else None
    target.created_at = agent.created_at
    return target


def agent_version_to_orm(version: AgentVersion) -> AgentVersionOrm:
    return AgentVersionOrm(
        id=version.id.value,
        agent_id=version.agent_id.value,
        version_number=version.version_number.value,
        status=version.status.value,
        label=version.label,
        release_notes=version.release_notes,
        predecessor_version_id=(
            version.predecessor_version_id.value
            if version.predecessor_version_id
            else None
        ),
        created_at=version.created_at,
    )
