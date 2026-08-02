"""Adapter and Adapter Version ORM models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class AdapterOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Adapter (stable identity).

    Connected to exactly one Agent by reference — not owned by Agent
    (Schema Design / Domain Model independent versioning axes).
    """

    __tablename__ = "adapters"

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")


class AdapterVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Adapter Version (immutable)."""

    __tablename__ = "adapter_versions"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "version_number",
            name="uq_adapter_versions_adapter_id_version_number",
        ),
    )

    adapter_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("adapters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("adapter_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
