"""Prompt and Prompt Version ORM models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class PromptOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Prompt (stable identity, owned by Case)."""

    __tablename__ = "prompts"

    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )


class PromptVersionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Prompt Version (immutable)."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "prompt_id",
            "version_number",
            name="uq_prompt_versions_prompt_id_version_number",
        ),
    )

    prompt_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    predecessor_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
