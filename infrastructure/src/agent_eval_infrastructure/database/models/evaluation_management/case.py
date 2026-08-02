"""Case and Case Version ORM models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class CaseOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Case (stable identity)."""

    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_cases_project_id_name"),
    )

    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")


class CaseVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Case Version (immutable)."""

    __tablename__ = "case_versions"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "version_number",
            name="uq_case_versions_case_id_version_number",
        ),
    )

    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repository_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(128), nullable=False)
    subdirectory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    expected_checks: Mapped[list[Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=list,
    )
    prompt_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("case_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
