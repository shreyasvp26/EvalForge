"""Project ORM model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)

# JSONB on PostgreSQL; portable JSON elsewhere (tests on SQLite).
_JsonType = JSON().with_variant(JSONB(), "postgresql")


class ProjectOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Project (Schema Design)."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    settings: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
