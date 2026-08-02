"""Score ORM model — one per Run × Grader Version."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    UuidPrimaryKeyMixin,
)

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class ScoreOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Score (immutable; uniqueness enables idempotent inserts)."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "grader_version_id",
            name="uq_scores_run_id_grader_version_id",
        ),
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grader_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("graders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    grader_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("grader_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    categorical_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
    )
    explanation_artifact_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("artifacts.id", ondelete="RESTRICT"),
        nullable=True,
    )
