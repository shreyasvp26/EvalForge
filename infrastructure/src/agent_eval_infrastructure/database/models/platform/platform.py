"""Platform catalog ORM models."""

from __future__ import annotations

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


class PlatformOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platforms"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")


class PlatformVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "platform_versions"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "version_number",
            name="uq_platform_versions_platform_id_version_number",
        ),
    )

    platform_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("platforms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sandbox_policy: Mapped[dict[str, str]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    execution_policy: Mapped[dict[str, str]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    timeout_policy: Mapped[dict[str, str]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    environment_policy: Mapped[dict[str, str]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    grading_policy: Mapped[dict[str, str]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("platform_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
