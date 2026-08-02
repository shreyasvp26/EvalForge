"""Project membership persistence — Infrastructure storage only.

Authorization *policy* (role ranks) lives in the API composition root that
implements ``AuthorizationPort``. This module only stores actor↔project roles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)
from agent_eval_infrastructure.database.session import SessionFactory


class ProjectRole(StrEnum):
    """Project-scoped RBAC roles (REST Authorization — Project membership)."""

    OWNER = "owner"
    ADMIN = "admin"
    MAINTAINER = "maintainer"
    VIEWER = "viewer"


ROLE_RANK: dict[ProjectRole, int] = {
    ProjectRole.VIEWER: 1,
    ProjectRole.MAINTAINER: 2,
    ProjectRole.ADMIN: 3,
    ProjectRole.OWNER: 4,
}


class ProjectMembershipOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Operational membership row — not a Domain aggregate."""

    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "actor_id",
            name="uq_project_memberships_project_id_actor_id",
        ),
    )

    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)


class MembershipStore(Protocol):
    def get_role(self, *, actor_id: str, project_id: str) -> ProjectRole | None: ...

    def upsert(
        self,
        *,
        actor_id: str,
        project_id: str,
        role: ProjectRole,
    ) -> None: ...


@dataclass
class InMemoryMembershipStore:
    """Process-local membership store for tests / MEMORY profile."""

    _roles: dict[tuple[str, str], ProjectRole] = field(default_factory=dict)

    def get_role(self, *, actor_id: str, project_id: str) -> ProjectRole | None:
        return self._roles.get((project_id, actor_id))

    def upsert(
        self,
        *,
        actor_id: str,
        project_id: str,
        role: ProjectRole,
    ) -> None:
        self._roles[(project_id, actor_id)] = role


@dataclass(slots=True)
class SqlAlchemyMembershipStore:
    """PostgreSQL-backed membership store."""

    session_factory: SessionFactory

    def get_role(self, *, actor_id: str, project_id: str) -> ProjectRole | None:
        with self.session_factory() as session:
            row = self._get(session, actor_id=actor_id, project_id=project_id)
            if row is None:
                return None
            return ProjectRole(row.role)

    def upsert(
        self,
        *,
        actor_id: str,
        project_id: str,
        role: ProjectRole,
    ) -> None:
        with self.session_factory() as session:
            row = self._get(session, actor_id=actor_id, project_id=project_id)
            if row is None:
                session.add(
                    ProjectMembershipOrm(
                        project_id=project_id,
                        actor_id=actor_id,
                        role=role.value,
                    )
                )
            else:
                row.role = role.value
            session.commit()

    @staticmethod
    def _get(
        session: Session,
        *,
        actor_id: str,
        project_id: str,
    ) -> ProjectMembershipOrm | None:
        stmt = select(ProjectMembershipOrm).where(
            ProjectMembershipOrm.project_id == project_id,
            ProjectMembershipOrm.actor_id == actor_id,
        )
        return session.execute(stmt).scalar_one_or_none()
