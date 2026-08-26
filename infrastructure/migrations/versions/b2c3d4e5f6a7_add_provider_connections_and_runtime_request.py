"""Add runs.runtime_request for create-time provider/model/credential pins."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "runtime_request",
            _JsonType,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("credential_ref_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider_key",
            "display_name",
            name="uq_provider_connections_user_provider_name",
        ),
    )


def downgrade() -> None:
    op.drop_table("provider_connections")
    op.drop_column("runs", "runtime_request")
