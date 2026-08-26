"""add platform version catalog

Revision ID: 9a4d7c2e5b81
Revises: f8c5d2e16a30
Create Date: 2026-08-26 02:10:00.000000

Runs are validated against the catalog in the application layer. This migration
intentionally does not add a runs.platform_version_id foreign key because
historical deployments may contain valid legacy free-text pins.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9a4d7c2e5b81"
down_revision: str | None = "f8c5d2e16a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platforms")),
    )
    op.create_table(
        "platform_versions",
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("sandbox_policy", _JsonType, nullable=False),
        sa.Column("execution_policy", _JsonType, nullable=False),
        sa.Column("timeout_policy", _JsonType, nullable=False),
        sa.Column("environment_policy", _JsonType, nullable=False),
        sa.Column("grading_policy", _JsonType, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("predecessor_version_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
            name=op.f("fk_platform_versions_platform_id_platforms"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_version_id"],
            ["platform_versions.id"],
            name=op.f("fk_platform_versions_predecessor_version_id_platform_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_versions")),
        sa.UniqueConstraint(
            "platform_id",
            "version_number",
            name="uq_platform_versions_platform_id_version_number",
        ),
    )
    op.create_index(
        op.f("ix_platform_versions_platform_id"),
        "platform_versions",
        ["platform_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_platform_versions_platform_id"),
        table_name="platform_versions",
    )
    op.drop_table("platform_versions")
    op.drop_table("platforms")
