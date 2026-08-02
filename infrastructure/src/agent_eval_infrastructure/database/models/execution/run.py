"""Run ORM model — aggregate root for execution facts."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class RunOrm(UuidPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    """Logical table: Run.

    Status is the sole legitimate mutation target on an otherwise append-only
    entity (Schema Design). ``lock_version`` supports optimistic concurrency
    for status transitions (Database Design §Concurrency).
    """

    __tablename__ = "runs"

    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("case_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prompt_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    adapter_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("adapter_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    platform_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    suite_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("suite_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Execution cost facts — primary observations, not derived (Schema Design).
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wall_clock_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compute_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
