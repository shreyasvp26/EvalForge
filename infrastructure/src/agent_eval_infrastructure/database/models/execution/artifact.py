"""Artifact ORM model — metadata + object-storage reference."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    CreatedAtMixin,
    UuidPrimaryKeyMixin,
)


class ArtifactOrm(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logical table: Artifact (immutable metadata; payload in object storage)."""

    __tablename__ = "artifacts"

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    produced_by_grader_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("grader_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
