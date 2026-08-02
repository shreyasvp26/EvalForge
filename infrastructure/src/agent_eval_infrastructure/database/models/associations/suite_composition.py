"""Suite Composition association ORM model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    UuidPrimaryKeyMixin,
)


class SuiteCompositionOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Suite Composition (ordered Case Versions in a Suite Version)."""

    __tablename__ = "suite_compositions"
    __table_args__ = (
        UniqueConstraint(
            "suite_version_id",
            "case_version_id",
            name="uq_suite_compositions_suite_version_id_case_version_id",
        ),
        UniqueConstraint(
            "suite_version_id",
            "position",
            name="uq_suite_compositions_suite_version_id_position",
        ),
    )

    suite_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("suite_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("case_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
