"""SQLAlchemy PlatformRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import PlatformId, PlatformVersionId
from agent_eval_domain.platform.platform import Platform, PlatformVersion
from sqlalchemy import select

from agent_eval_infrastructure.database.models.platform import (
    PlatformOrm,
    PlatformVersionOrm,
)
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.mappers.platform import (
    platform_to_domain,
    platform_to_orm,
    platform_version_to_domain,
    platform_version_to_orm,
)
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyPlatformRepository(SqlAlchemyRepository):
    def get(self, platform_id: PlatformId) -> Platform:
        row = self.session.get(PlatformOrm, platform_id.value)
        require_found(row, entity_type="Platform", entity_id=platform_id.value)
        return self._load_platform(row)  # type: ignore[arg-type]

    def get_version(self, version_id: PlatformVersionId) -> PlatformVersion:
        row = self.session.get(PlatformVersionOrm, version_id.value)
        require_found(row, entity_type="PlatformVersion", entity_id=version_id.value)
        return platform_version_to_domain(row)  # type: ignore[arg-type]

    def save(self, platform: Platform) -> None:
        row = self.session.get(PlatformOrm, platform.id.value)
        mapped = platform_to_orm(platform, row)
        if row is None:
            self.session.add(mapped)
        for version in platform.versions:
            version_row = self.session.get(PlatformVersionOrm, version.id.value)
            if version_row is None:
                self.session.add(platform_version_to_orm(version))
            else:
                version_row.status = version.status.value

    def list_all(self) -> list[Platform]:
        rows = list(self.session.scalars(select(PlatformOrm)))
        return [self._load_platform(row) for row in rows]

    def _load_platform(self, row: PlatformOrm) -> Platform:
        versions = list(
            self.session.scalars(
                select(PlatformVersionOrm).where(
                    PlatformVersionOrm.platform_id == row.id
                )
            )
        )
        return platform_to_domain(row, versions)
