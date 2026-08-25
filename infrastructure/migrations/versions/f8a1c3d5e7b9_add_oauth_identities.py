"""add oauth identities and nullable password hash

Revision ID: f8a1c3d5e7b9
Revises: e7b4a1c05f29
Create Date: 2026-08-26 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8a1c3d5e7b9"
down_revision: str | None = "e7b4a1c05f29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.create_table(
        "oauth_identities",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=128), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_oauth_identities_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_identities")),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_identities_provider_subject",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            name="uq_oauth_identities_user_provider",
        ),
    )
    op.create_index(
        op.f("ix_oauth_identities_user_id"),
        "oauth_identities",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_identities_user_id"), table_name="oauth_identities")
    op.drop_table("oauth_identities")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=512),
        nullable=False,
    )
