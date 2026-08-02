"""Reusable ORM column mixins.

These encode storage shape only — timestamps, opaque string primary keys,
and optimistic concurrency tokens for the few legitimately mutable rows
(Database Design §Concurrency / Schema Design §Run status).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class UuidPrimaryKeyMixin:
    """Opaque string primary key (Application/Infrastructure generates IDs).

    Domain IDs are non-empty opaque strings; UUID is the default generation
    strategy, stored as text for driver portability.
    """

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class TimestampMixin:
    """Created/updated timestamps for definitional and mutable rows."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
        default=utc_now,
    )


class CreatedAtMixin:
    """Created-at only — for append-only / immutable version rows."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utc_now,
    )


class OptimisticLockMixin:
    """Integer version token for optimistic concurrency (Run status, etc.)."""

    lock_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
