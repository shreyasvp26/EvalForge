"""Execution Event ORM model — append-only."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import UuidPrimaryKeyMixin, utc_now

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class ExecutionEventOrm(UuidPrimaryKeyMixin, Base):
    """Logical table: Execution Event (append-only, ordered within a Run)."""

    __tablename__ = "execution_events"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "sequence",
            name="uq_execution_events_run_id_sequence",
        ),
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    action_payload: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utc_now,
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
    artifact_ids: Mapped[list[Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=list,
    )
