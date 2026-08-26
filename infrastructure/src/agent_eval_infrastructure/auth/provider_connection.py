"""Provider connection persistence — encrypted BYOK secrets.

Follows the IdentityPort pattern: Application talks through
``ProviderConnectionPort``; Infrastructure owns ORM + Fernet ciphertext.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from agent_eval_application.ports.provider_connections import (
    CreateProviderConnectionInput,
    ProviderConnectionPort,
)
from agent_eval_domain.common.errors import InvariantViolation, NotFoundError
from agent_eval_domain.execution.credentials import (
    CredentialBackend,
    CredentialReference,
)
from agent_eval_domain.execution.provider_connection import (
    ProviderConnection,
    ProviderConnectionStatus,
)
from agent_eval_domain.execution.provider_runtime import ProviderKey, parse_provider_key
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


class ProviderConnectionOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider_key",
            "display_name",
            name="uq_provider_connections_user_provider_name",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_ref_id: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict
    )
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)


def _credential_ref_id(*, user_id: str, connection_id: str) -> str:
    return f"user:{user_id}:conn:{connection_id}"


def _to_domain(row: ProviderConnectionOrm) -> ProviderConnection:
    return ProviderConnection(
        id=row.id,
        user_id=row.user_id,
        provider_key=parse_provider_key(row.provider_key),
        credential_ref_id=row.credential_ref_id,
        display_name=row.display_name,
        status=ProviderConnectionStatus(row.status),
        created_at=row.created_at,
        key_fingerprint=row.key_fingerprint,
        metadata={str(k): str(v) for k, v in dict(row.metadata_json or {}).items()},
    )


class SqlAlchemyProviderConnectionStore(ProviderConnectionPort):
    """User-scoped provider connections with encrypted secrets."""

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

    def create(self, input: CreateProviderConnectionInput) -> ProviderConnection:
        secret = input.api_key.strip()
        if not secret:
            raise InvariantViolation(
                "api_key must be non-empty",
                code="EMPTY_PROVIDER_API_KEY",
            )
        provider = parse_provider_key(input.provider_key)
        connection_id = str(uuid4())
        credential_ref_id = _credential_ref_id(
            user_id=input.user_id, connection_id=connection_id
        )
        row = ProviderConnectionOrm(
            id=connection_id,
            user_id=input.user_id.strip(),
            provider_key=provider.value,
            credential_ref_id=credential_ref_id,
            display_name=input.display_name.strip() or provider.value.title(),
            status=ProviderConnectionStatus.ACTIVE.value,
            key_fingerprint=fingerprint_secret(secret),
            metadata_json=dict(input.metadata or {}),
            secret_ciphertext=encrypt_secret(secret, key=self._key()),
        )
        with self._session_factory() as session:
            session: Session
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def list_for_user(self, user_id: str) -> list[ProviderConnection]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProviderConnectionOrm)
                .where(ProviderConnectionOrm.user_id == user_id)
                .order_by(ProviderConnectionOrm.created_at.desc())
            ).all()
            return [_to_domain(row) for row in rows]

    def get_for_user(self, *, user_id: str, connection_id: str) -> ProviderConnection:
        with self._session_factory() as session:
            row = session.get(ProviderConnectionOrm, connection_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError(
                    f"Provider connection {connection_id!r} not found",
                    entity="ProviderConnection",
                    entity_id=connection_id,
                )
            return _to_domain(row)

    def revoke_for_user(
        self, *, user_id: str, connection_id: str
    ) -> ProviderConnection:
        with self._session_factory() as session:
            row = session.get(ProviderConnectionOrm, connection_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError(
                    f"Provider connection {connection_id!r} not found",
                    entity="ProviderConnection",
                    entity_id=connection_id,
                )
            row.status = ProviderConnectionStatus.REVOKED.value
            row.updated_at = datetime.now(UTC)
            # Wipe ciphertext so revoked secrets cannot be recovered.
            row.secret_ciphertext = encrypt_secret(
                f"revoked-{uuid4()}", key=self._key()
            )
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def resolve_secret_for_user(
        self, *, user_id: str, credential_ref_id: str
    ) -> tuple[ProviderConnection, str]:
        with self._session_factory() as session:
            row = session.scalars(
                select(ProviderConnectionOrm).where(
                    ProviderConnectionOrm.credential_ref_id == credential_ref_id,
                    ProviderConnectionOrm.user_id == user_id,
                )
            ).first()
            if row is None:
                raise NotFoundError(
                    f"Credential reference {credential_ref_id!r} not found",
                    entity="CredentialReference",
                    entity_id=credential_ref_id,
                )
            connection = _to_domain(row)
            if not connection.is_usable:
                raise InvariantViolation(
                    "Provider connection is revoked and cannot be used",
                    code="PROVIDER_CONNECTION_REVOKED",
                    details={"provider_connection_id": connection.id},
                )
            secret = decrypt_secret(row.secret_ciphertext, key=self._key())
            return connection, secret

    def credential_reference_for(
        self, connection: ProviderConnection
    ) -> CredentialReference:
        return CredentialReference(
            id=connection.credential_ref_id,
            provider_key=connection.provider_key,
            label=connection.display_name,
            backend=CredentialBackend.USER_SECRET_STORE,
            env_var_name=None,
        )


class InMemoryProviderConnectionStore(ProviderConnectionPort):
    """Dict-backed store for MEMORY profile and unit tests."""

    def __init__(self, *, secret_key: bytes | None = None) -> None:
        self._rows: dict[str, dict[str, Any]] = {}
        self._secret_key = secret_key

    def _key(self) -> bytes:
        return self._secret_key or load_provider_secret_key()

    def create(self, input: CreateProviderConnectionInput) -> ProviderConnection:
        secret = input.api_key.strip()
        if not secret:
            raise InvariantViolation(
                "api_key must be non-empty",
                code="EMPTY_PROVIDER_API_KEY",
            )
        provider = parse_provider_key(input.provider_key)
        connection_id = str(uuid4())
        credential_ref_id = _credential_ref_id(
            user_id=input.user_id, connection_id=connection_id
        )
        now = datetime.now(UTC)
        self._rows[connection_id] = {
            "id": connection_id,
            "user_id": input.user_id.strip(),
            "provider_key": provider.value,
            "credential_ref_id": credential_ref_id,
            "display_name": input.display_name.strip() or provider.value.title(),
            "status": ProviderConnectionStatus.ACTIVE.value,
            "created_at": now,
            "key_fingerprint": fingerprint_secret(secret),
            "metadata": dict(input.metadata or {}),
            "secret_ciphertext": encrypt_secret(secret, key=self._key()),
        }
        return self._to_domain(self._rows[connection_id])

    def list_for_user(self, user_id: str) -> list[ProviderConnection]:
        rows = [row for row in self._rows.values() if row["user_id"] == user_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [self._to_domain(row) for row in rows]

    def get_for_user(self, *, user_id: str, connection_id: str) -> ProviderConnection:
        row = self._rows.get(connection_id)
        if row is None or row["user_id"] != user_id:
            raise NotFoundError(
                f"Provider connection {connection_id!r} not found",
                entity="ProviderConnection",
                entity_id=connection_id,
            )
        return self._to_domain(row)

    def revoke_for_user(
        self, *, user_id: str, connection_id: str
    ) -> ProviderConnection:
        row = self._rows.get(connection_id)
        if row is None or row["user_id"] != user_id:
            raise NotFoundError(
                f"Provider connection {connection_id!r} not found",
                entity="ProviderConnection",
                entity_id=connection_id,
            )
        row["status"] = ProviderConnectionStatus.REVOKED.value
        row["secret_ciphertext"] = encrypt_secret(f"revoked-{uuid4()}", key=self._key())
        return self._to_domain(row)

    def resolve_secret_for_user(
        self, *, user_id: str, credential_ref_id: str
    ) -> tuple[ProviderConnection, str]:
        for row in self._rows.values():
            if (
                row["credential_ref_id"] == credential_ref_id
                and row["user_id"] == user_id
            ):
                connection = self._to_domain(row)
                if not connection.is_usable:
                    raise InvariantViolation(
                        "Provider connection is revoked and cannot be used",
                        code="PROVIDER_CONNECTION_REVOKED",
                        details={"provider_connection_id": connection.id},
                    )
                secret = decrypt_secret(row["secret_ciphertext"], key=self._key())
                return connection, secret
        raise NotFoundError(
            f"Credential reference {credential_ref_id!r} not found",
            entity="CredentialReference",
            entity_id=credential_ref_id,
        )

    @staticmethod
    def _to_domain(row: dict[str, Any]) -> ProviderConnection:
        return ProviderConnection(
            id=row["id"],
            user_id=row["user_id"],
            provider_key=parse_provider_key(row["provider_key"]),
            credential_ref_id=row["credential_ref_id"],
            display_name=row["display_name"],
            status=ProviderConnectionStatus(row["status"]),
            created_at=row["created_at"],
            key_fingerprint=row["key_fingerprint"],
            metadata={
                str(k): str(v) for k, v in dict(row.get("metadata") or {}).items()
            },
        )


# Re-export ProviderKey for type checkers importing from this module.
__all__ = [
    "InMemoryProviderConnectionStore",
    "ProviderConnectionOrm",
    "SqlAlchemyProviderConnectionStore",
    "ProviderKey",
]
