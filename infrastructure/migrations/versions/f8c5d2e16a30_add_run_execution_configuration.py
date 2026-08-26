"""add run execution configuration

Revision ID: f8c5d2e16a30
Revises: e7b4a1c05f29
Create Date: 2026-08-26 01:50:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8c5d2e16a30"
down_revision: str | None = "e7b4a1c05f29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("execution_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "runs",
        sa.Column(
            "execution_metadata",
            _JsonType,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "execution_metadata")
    op.drop_column("runs", "execution_mode")
