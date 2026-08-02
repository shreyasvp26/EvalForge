"""Grader and Grader Version ORM models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class GraderOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Grader (stable identity)."""

    __tablename__ = "graders"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")


class GraderVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Grader Version (immutable)."""

    __tablename__ = "grader_versions"
    __table_args__ = (
        UniqueConstraint(
            "grader_id",
            "version_number",
            name="uq_grader_versions_grader_id_version_number",
        ),
    )

    grader_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("graders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    specification: Mapped[str] = mapped_column(Text, nullable=False)
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("grader_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
