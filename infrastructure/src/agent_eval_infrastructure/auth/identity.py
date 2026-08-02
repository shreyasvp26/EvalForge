"""User identity persistence — Infrastructure storage only.

Credential hashing and user rows live here. Application talks only through
``IdentityPort``; JWT minting stays in the API Layer.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_application.ports.identity import IdentityPort, IdentityRecord
from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)
from agent_eval_infrastructure.database.session import SessionFactory

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64
_HASH_PREFIX = "scrypt"


def hash_password(password: str) -> str:
    """Hash a password with scrypt (stdlib — no extra dependency)."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return (
        f"{_HASH_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify against a ``hash_password`` encoding."""
    try:
        prefix, n_s, r_s, p_s, salt_hex, digest_hex = encoded.split("$", 5)
    except ValueError:
        return False
    if prefix != _HASH_PREFIX:
        return False
    try:
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(bytes.fromhex(digest_hex)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


class UserOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Operational identity row — not a Domain aggregate."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)


@dataclass(frozen=True, slots=True)
class StoredUser:
    id: str
    email: str
    display_name: str
    password_hash: str

    def to_record(self) -> IdentityRecord:
        return IdentityRecord(
            id=self.id,
            email=self.email,
            display_name=self.display_name,
        )


@dataclass
class InMemoryIdentityStore:
    """Process-local identity store for tests / MEMORY profile."""

    _users_by_id: dict[str, StoredUser] = field(default_factory=dict)
    _ids_by_email: dict[str, str] = field(default_factory=dict)

    def authenticate(self, *, email: str, password: str) -> IdentityRecord | None:
        normalized = email.strip().lower()
        user_id = self._ids_by_email.get(normalized)
        if user_id is None:
            return None
        user = self._users_by_id[user_id]
        if not verify_password(password, user.password_hash):
            return None
        return user.to_record()

    def get_by_id(self, user_id: str) -> IdentityRecord | None:
        user = self._users_by_id.get(user_id)
        return user.to_record() if user is not None else None

    def upsert(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        user_id: str | None = None,
    ) -> IdentityRecord:
        normalized = email.strip().lower()
        existing_id = self._ids_by_email.get(normalized)
        resolved_id = existing_id or user_id or str(uuid4())
        stored = StoredUser(
            id=resolved_id,
            email=normalized,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
        )
        self._users_by_id[resolved_id] = stored
        self._ids_by_email[normalized] = resolved_id
        return stored.to_record()


@dataclass(slots=True)
class SqlAlchemyIdentityStore:
    """PostgreSQL-backed identity store."""

    session_factory: SessionFactory

    def authenticate(self, *, email: str, password: str) -> IdentityRecord | None:
        normalized = email.strip().lower()
        with self.session_factory() as session:
            row = self._get_by_email(session, normalized)
            if row is None:
                return None
            if not verify_password(password, row.password_hash):
                return None
            return IdentityRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
            )

    def get_by_id(self, user_id: str) -> IdentityRecord | None:
        with self.session_factory() as session:
            row = session.get(UserOrm, user_id)
            if row is None:
                return None
            return IdentityRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
            )

    def upsert(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        user_id: str | None = None,
    ) -> IdentityRecord:
        normalized = email.strip().lower()
        with self.session_factory() as session:
            row = self._get_by_email(session, normalized)
            if row is None:
                row = UserOrm(
                    id=user_id or str(uuid4()),
                    email=normalized,
                    display_name=display_name.strip(),
                    password_hash=hash_password(password),
                )
                session.add(row)
            else:
                row.display_name = display_name.strip()
                row.password_hash = hash_password(password)
            session.commit()
            session.refresh(row)
            return IdentityRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
            )

    @staticmethod
    def _get_by_email(session: Session, email: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.email == email)
        return session.execute(stmt).scalar_one_or_none()


def ensure_bootstrap_user(
    store: IdentityPort,
    *,
    email: str,
    password: str,
    display_name: str,
) -> IdentityRecord | None:
    """Create or refresh a bootstrap user when credentials are configured.

    Stores that support ``upsert`` (both in-memory and SQLAlchemy) are updated;
    unknown store types are left unchanged.
    """
    if not email.strip() or not password:
        return None
    upsert = getattr(store, "upsert", None)
    if not callable(upsert):
        return None
    return upsert(email=email, password=password, display_name=display_name)
