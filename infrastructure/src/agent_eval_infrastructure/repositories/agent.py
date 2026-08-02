"""SQLAlchemy AgentRepository adapter."""

from __future__ import annotations

from agent_eval_domain.agent_integration.agent import Agent
from agent_eval_domain.common.ids import AgentId
from sqlalchemy import select

from agent_eval_infrastructure.database.models.agent_integration.agent import (
    AgentOrm,
    AgentVersionOrm,
)
from agent_eval_infrastructure.mappers.agent import (
    agent_to_domain,
    agent_to_orm,
    agent_version_to_orm,
)
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyAgentRepository(SqlAlchemyRepository):
    def get(self, agent_id: AgentId) -> Agent:
        row = self.session.get(AgentOrm, agent_id.value)
        require_found(row, entity_type="Agent", entity_id=agent_id.value)
        return self._load_agent(row)  # type: ignore[arg-type]

    def save(self, agent: Agent) -> None:
        row = self.session.get(AgentOrm, agent.id.value)
        mapped = agent_to_orm(agent, row)
        if row is None:
            self.session.add(mapped)

        for version in agent.versions:
            version_row = self.session.get(AgentVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(agent_version_to_orm(version))
            else:
                version_row.status = version.status.value

    def list_all(self) -> list[Agent]:
        rows = list(self.session.scalars(select(AgentOrm)))
        return [self._load_agent(row) for row in rows]

    def _load_agent(self, row: AgentOrm) -> Agent:
        versions = list(
            self.session.scalars(
                select(AgentVersionOrm).where(AgentVersionOrm.agent_id == row.id)
            )
        )
        return agent_to_domain(row, versions)
