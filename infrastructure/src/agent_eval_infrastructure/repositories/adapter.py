"""SQLAlchemy AdapterRepository adapter."""

from __future__ import annotations

from agent_eval_domain.agent_integration.adapter import Adapter
from agent_eval_domain.common.ids import AdapterId, AgentId
from sqlalchemy import select

from agent_eval_infrastructure.database.models.agent_integration.adapter import (
    AdapterOrm,
    AdapterVersionOrm,
)
from agent_eval_infrastructure.mappers.adapter import (
    adapter_to_domain,
    adapter_to_orm,
    adapter_version_to_orm,
)
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyAdapterRepository(SqlAlchemyRepository):
    def get(self, adapter_id: AdapterId) -> Adapter:
        row = self.session.get(AdapterOrm, adapter_id.value)
        require_found(row, entity_type="Adapter", entity_id=adapter_id.value)
        return self._load_adapter(row)  # type: ignore[arg-type]

    def get_by_agent(self, agent_id: AgentId) -> Adapter:
        row = self.session.scalars(
            select(AdapterOrm).where(AdapterOrm.agent_id == agent_id.value)
        ).first()
        require_found(
            row,
            entity_type="Adapter",
            entity_id=f"agent:{agent_id.value}",
        )
        return self._load_adapter(row)  # type: ignore[arg-type]

    def save(self, adapter: Adapter) -> None:
        row = self.session.get(AdapterOrm, adapter.id.value)
        mapped = adapter_to_orm(adapter, row)
        if row is None:
            self.session.add(mapped)

        for version in adapter.versions:
            version_row = self.session.get(AdapterVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(adapter_version_to_orm(version))
            else:
                version_row.status = version.status.value

    def list_all(self) -> list[Adapter]:
        rows = list(self.session.scalars(select(AdapterOrm)))
        return [self._load_adapter(row) for row in rows]

    def _load_adapter(self, row: AdapterOrm) -> Adapter:
        versions = list(
            self.session.scalars(
                select(AdapterVersionOrm).where(AdapterVersionOrm.adapter_id == row.id)
            )
        )
        return adapter_to_domain(row, versions)
