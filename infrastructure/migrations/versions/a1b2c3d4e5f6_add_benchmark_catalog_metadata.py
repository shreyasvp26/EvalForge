"""add benchmark catalog metadata

Revision ID: a1b2c3d4e5f6
Revises: f8a1c3d5e7b9
Create Date: 2026-08-26

Extends Suite/Case discovery fields and Run execution_group_id so published
SuiteVersions can act as a benchmark catalog without a second aggregate.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f8a1c3d5e7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "suites",
        sa.Column(
            "catalog_key", sa.String(length=128), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "suites",
        sa.Column(
            "catalog_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index("ix_suites_catalog_visible", "suites", ["catalog_visible"])

    op.add_column(
        "cases",
        sa.Column("category", sa.String(length=128), nullable=False, server_default=""),
    )
    op.add_column(
        "cases",
        sa.Column(
            "difficulty", sa.String(length=64), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "cases",
        sa.Column("language", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "cases",
        sa.Column("tags", _JsonType, nullable=False, server_default=sa.text("'[]'")),
    )

    op.add_column(
        "runs",
        sa.Column("execution_group_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_runs_execution_group_id", "runs", ["execution_group_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_execution_group_id", table_name="runs")
    op.drop_column("runs", "execution_group_id")

    op.drop_column("cases", "tags")
    op.drop_column("cases", "language")
    op.drop_column("cases", "difficulty")
    op.drop_column("cases", "category")

    op.drop_index("ix_suites_catalog_visible", table_name="suites")
    op.drop_column("suites", "catalog_visible")
    op.drop_column("suites", "catalog_key")
