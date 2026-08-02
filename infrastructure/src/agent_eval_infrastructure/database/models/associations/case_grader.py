"""Case Grader Declaration association ORM model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    UuidPrimaryKeyMixin,
)


class CaseGraderDeclarationOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Case Grader Declaration (Case Version × Grader)."""

    __tablename__ = "case_grader_declarations"
    __table_args__ = (
        UniqueConstraint(
            "case_version_id",
            "grader_id",
            name="uq_case_grader_declarations_case_version_id_grader_id",
        ),
    )

    case_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("case_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grader_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("graders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
