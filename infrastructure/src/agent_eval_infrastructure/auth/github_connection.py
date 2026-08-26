"""GitHub connection persistence — encrypted publication tokens.

Reuses Fernet secret box from provider connections. Tokens are never returned
through public APIs after create.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from agent_eval_application.ports.github_publication import (
    CreateGitHubConnectionInput,
    GitHubConnection,
    GitHubConnectionPort,
)
from agent_eval_domain.common.errors import InvariantViolation, NotFoundError
from sqlalchemy import String, Text, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import JSON

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)
from agent_eval_infrastructure.database.session import SessionFactory
from agent_eval_infrastructure.secrets.fernet_box import (
    decrypt_secret,
    encrypt_secret,
    fingerprint_secret,
    load_provider_secret_key,
)

_JsonType = JSON().with_variant(JSONB(), "postgresql")


class GitHubConnectionOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "github_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "display_name",
            name="uq_github_connections_user_display_name",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes_json: Mapped[list[Any]] = mapped_column(_JsonType, nullable=False)
    github_login: Mapped[str | None] = mapped_column(String(200), nullable=True)
    key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)


def _to_port(row: GitHubConnectionOrm) -> GitHubConnection:
    return GitHubConnection(
        id=row.id,
        user_id=row.user_id,
        display_name=row.display_name,
        status=row.status,
        scopes=tuple(str(s) for s in list(row.scopes_json or [])),
        github_login=row.github_login,
        key_fingerprint=row.key_fingerprint,
        created_at=row.created_at.isoformat(),
        metadata={str(k): str(v) for k, v in dict(row.metadata_json or {}).items()},
    )


class SqlAlchemyGitHubConnectionStore(GitHubConnectionPort):
    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        secret_key: bytes | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._secret_key = secret_key

    def _key(self) -> bytes:
        return self._secret_key or load_provider_secret_key()

    def create(self, input: CreateGitHubConnectionInput) -> GitHubConnection:
        token = input.token.strip()
        if not token:
            raise InvariantViolation(
                "GitHub token must be non-empty",
                code="EMPTY_GITHUB_TOKEN",
            )
        connection_id = str(uuid4())
        row = GitHubConnectionOrm(
            id=connection_id,
            user_id=input.user_id.strip(),
            display_name=input.display_name.strip() or "GitHub",
            status="active",
            scopes_json=list(input.scopes or ("repo",)),
            github_login=input.github_login,
            key_fingerprint=fingerprint_secret(token),
            metadata_json=dict(input.metadata or {}),
            secret_ciphertext=encrypt_secret(token, key=self._key()),
        )
        with self._session_factory() as session:
            session: Session
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_port(row)

    def list_for_user(self, user_id: str) -> list[GitHubConnection]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(GitHubConnectionOrm)
                .where(GitHubConnectionOrm.user_id == user_id)
                .order_by(GitHubConnectionOrm.created_at.desc())
            ).all()
            return [_to_port(row) for row in rows]

    def get_for_user(self, *, user_id: str, connection_id: str) -> GitHubConnection:
        with self._session_factory() as session:
            row = session.get(GitHubConnectionOrm, connection_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError(
                    f"GitHub connection {connection_id!r} not found",
                    entity="GitHubConnection",
                    entity_id=connection_id,
                )
            return _to_port(row)

    def revoke_for_user(self, *, user_id: str, connection_id: str) -> GitHubConnection:
        with self._session_factory() as session:
            row = session.get(GitHubConnectionOrm, connection_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError(
                    f"GitHub connection {connection_id!r} not found",
                    entity="GitHubConnection",
                    entity_id=connection_id,
                )
            row.status = "revoked"
            row.updated_at = datetime.now(UTC)
            row.secret_ciphertext = encrypt_secret(
                f"revoked-{uuid4()}", key=self._key()
            )
            session.commit()
            session.refresh(row)
            return _to_port(row)

    def resolve_token_for_user(
        self, *, user_id: str, connection_id: str | None = None
    ) -> tuple[GitHubConnection, str]:
        with self._session_factory() as session:
            if connection_id:
                row = session.get(GitHubConnectionOrm, connection_id)
                if row is None or row.user_id != user_id:
                    raise NotFoundError(
                        f"GitHub connection {connection_id!r} not found",
                        entity="GitHubConnection",
                        entity_id=connection_id or "",
                    )
            else:
                row = session.scalars(
                    select(GitHubConnectionOrm)
                    .where(
                        GitHubConnectionOrm.user_id == user_id,
                        GitHubConnectionOrm.status == "active",
                    )
                    .order_by(GitHubConnectionOrm.created_at.desc())
                ).first()
                if row is None:
                    raise NotFoundError(
                        "No active GitHub connection for user",
                        entity="GitHubConnection",
                        entity_id=user_id,
                    )
            connection = _to_port(row)
            if connection.status != "active":
                raise InvariantViolation(
                    "GitHub connection is revoked and cannot be used",
                    code="GITHUB_CONNECTION_REVOKED",
                    details={"github_connection_id": connection.id},
                )
            token = decrypt_secret(row.secret_ciphertext, key=self._key())
            return connection, token


class InMemoryGitHubConnectionStore(GitHubConnectionPort):
    """Dict-backed store for MEMORY profile and unit tests."""

    def __init__(self, *, secret_key: bytes | None = None) -> None:
        self._rows: dict[str, dict[str, Any]] = {}
        self._secret_key = secret_key

    def _key(self) -> bytes:
        return self._secret_key or load_provider_secret_key()

    def create(self, input: CreateGitHubConnectionInput) -> GitHubConnection:
        token = input.token.strip()
        if not token:
            raise InvariantViolation(
                "GitHub token must be non-empty",
                code="EMPTY_GITHUB_TOKEN",
            )
        connection_id = str(uuid4())
        now = datetime.now(UTC)
        self._rows[connection_id] = {
            "id": connection_id,
            "user_id": input.user_id.strip(),
            "display_name": input.display_name.strip() or "GitHub",
            "status": "active",
            "scopes": list(input.scopes or ("repo",)),
            "github_login": input.github_login,
            "created_at": now.isoformat(),
            "key_fingerprint": fingerprint_secret(token),
            "metadata": dict(input.metadata or {}),
            "secret_ciphertext": encrypt_secret(token, key=self._key()),
        }
        return self._to_port(self._rows[connection_id])

    def list_for_user(self, user_id: str) -> list[GitHubConnection]:
        return [
            self._to_port(row)
            for row in self._rows.values()
            if row["user_id"] == user_id
        ]

    def get_for_user(self, *, user_id: str, connection_id: str) -> GitHubConnection:
        row = self._rows.get(connection_id)
        if row is None or row["user_id"] != user_id:
            raise NotFoundError(
                f"GitHub connection {connection_id!r} not found",
                entity="GitHubConnection",
                entity_id=connection_id,
            )
        return self._to_port(row)

    def revoke_for_user(self, *, user_id: str, connection_id: str) -> GitHubConnection:
        row = self._rows.get(connection_id)
        if row is None or row["user_id"] != user_id:
            raise NotFoundError(
                f"GitHub connection {connection_id!r} not found",
                entity="GitHubConnection",
                entity_id=connection_id,
            )
        row["status"] = "revoked"
        row["secret_ciphertext"] = encrypt_secret(f"revoked-{uuid4()}", key=self._key())
        return self._to_port(row)

    def resolve_token_for_user(
        self, *, user_id: str, connection_id: str | None = None
    ) -> tuple[GitHubConnection, str]:
        if connection_id:
            row = self._rows.get(connection_id)
            if row is None or row["user_id"] != user_id:
                raise NotFoundError(
                    f"GitHub connection {connection_id!r} not found",
                    entity="GitHubConnection",
                    entity_id=connection_id or "",
                )
        else:
            candidates = [
                r
                for r in self._rows.values()
                if r["user_id"] == user_id and r["status"] == "active"
            ]
            if not candidates:
                raise NotFoundError(
                    "No active GitHub connection for user",
                    entity="GitHubConnection",
                    entity_id=user_id,
                )
            row = candidates[0]
        connection = self._to_port(row)
        if connection.status != "active":
            raise InvariantViolation(
                "GitHub connection is revoked and cannot be used",
                code="GITHUB_CONNECTION_REVOKED",
            )
        token = decrypt_secret(row["secret_ciphertext"], key=self._key())
        return connection, token

    def _to_port(self, row: dict[str, Any]) -> GitHubConnection:
        return GitHubConnection(
            id=row["id"],
            user_id=row["user_id"],
            display_name=row["display_name"],
            status=row["status"],
            scopes=tuple(str(s) for s in list(row.get("scopes") or [])),
            github_login=row.get("github_login"),
            key_fingerprint=row["key_fingerprint"],
            created_at=str(row["created_at"]),
            metadata={
                str(k): str(v) for k, v in dict(row.get("metadata") or {}).items()
            },
        )
