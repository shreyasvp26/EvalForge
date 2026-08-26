"""Add runs.publication and github_connections for PR-on-PASS."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "publication",
            _JsonType,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_table(
        "github_connections",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scopes_json", _JsonType, nullable=False),
        sa.Column("github_login", sa.String(length=200), nullable=True),
        sa.Column("key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata_json",
            _JsonType,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "display_name",
            name="uq_github_connections_user_display_name",
        ),
    )


def downgrade() -> None:
    op.drop_table("github_connections")
    op.drop_column("runs", "publication")
