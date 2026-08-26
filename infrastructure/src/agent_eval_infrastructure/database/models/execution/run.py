"""Run ORM model — aggregate root for execution facts."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class RunOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Logical table: Run.

    Status is the sole legitimate mutation target on an otherwise append-only
    entity (Schema Design). ``lock_version`` supports optimistic concurrency
    for status transitions (Database Design §Concurrency).
    """

    __tablename__ = "runs"

    lock_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    __mapper_args__ = {"version_id_col": lock_version}

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
    execution_group_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    grader_version_ids: Mapped[list[Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=list,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    execution_metadata: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
    runtime_request: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wall_clock_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compute_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
