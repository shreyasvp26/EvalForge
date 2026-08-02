"""add project memberships

Revision ID: c4e8f1a29b07
Revises: b281bc762a8d
Create Date: 2026-08-02 16:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8f1a29b07"
down_revision: str | None = "b281bc762a8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_memberships")),
        sa.UniqueConstraint(
            "project_id",
            "actor_id",
            name="uq_project_memberships_project_id_actor_id",
        ),
    )
    op.create_index(
        op.f("ix_project_memberships_project_id"),
        "project_memberships",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_memberships_actor_id"),
        "project_memberships",
        ["actor_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_project_memberships_actor_id"),
        table_name="project_memberships",
    )
    op.drop_index(
        op.f("ix_project_memberships_project_id"),
        table_name="project_memberships",
    )
    op.drop_table("project_memberships")
