"""Agent and Agent Version ORM models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class AgentOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Agent (stable identity)."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    adapter_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "adapters.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_agents_adapter_id_adapters",
        ),
        nullable=True,
        index=True,
    )


class AgentVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Agent Version (immutable)."""

    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "version_number",
            name="uq_agent_versions_agent_id_version_number",
        ),
    )

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    release_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
