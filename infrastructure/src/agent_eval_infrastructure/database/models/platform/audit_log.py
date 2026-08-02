"""Audit Log ORM model — administrative/definitional action trail."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    UuidPrimaryKeyMixin,
)

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class AuditLogOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Audit Log (append-only; not owned by aggregates)."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
