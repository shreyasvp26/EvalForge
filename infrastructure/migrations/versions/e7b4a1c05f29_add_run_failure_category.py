"""add run failure_category

Revision ID: e7b4a1c05f29
Revises: d5a9c2b38e14
Create Date: 2026-08-25 19:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b4a1c05f29"
down_revision: str | None = "d5a9c2b38e14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("failure_category", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("runs", "failure_category")
