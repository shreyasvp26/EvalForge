"""Suite and Suite Version ORM models."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class SuiteOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Suite (stable identity)."""

    __tablename__ = "suites"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_suites_project_id_name"),
    )

    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    catalog_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    catalog_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")


class SuiteVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Suite Version (immutable)."""

    __tablename__ = "suite_versions"
    __table_args__ = (
        UniqueConstraint(
            "suite_id",
            "version_number",
            name="uq_suite_versions_suite_id_version_number",
        ),
    )

    suite_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("suites.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("suite_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
