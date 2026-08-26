"""OAuth identity persistence — links provider subjects to internal users."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_application.errors import AuthenticationError
from agent_eval_application.ports.identity import IdentityRecord
from agent_eval_application.ports.oauth_identity import (
    OAuthIdentityRecord,
    OAuthProvider,
    OAuthProviderIdentity,
)
from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from agent_eval_infrastructure.auth.identity import UserOrm
from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.mixins import (
    TimestampMixin,
    UuidPrimaryKeyMixin,
)
from agent_eval_infrastructure.database.session import SessionFactory


class OAuthIdentityOrm(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Provider subject linked to an internal user."""

    __tablename__ = "oauth_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_identities_provider_subject",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_oauth_identities_user_provider",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass
class InMemoryOAuthIdentityStore:
    """Process-local OAuth identity store for tests."""

    _by_provider_subject: dict[tuple[str, str], OAuthIdentityRecord] = field(
        default_factory=dict
    )
    _by_user_provider: dict[tuple[str, str], OAuthIdentityRecord] = field(
        default_factory=dict
    )
    _users_by_id: dict[str, IdentityRecord] = field(default_factory=dict)
    _ids_by_email: dict[str, str] = field(default_factory=dict)

    def seed_user(self, record: IdentityRecord) -> None:
        self._users_by_id[record.id] = record
        self._ids_by_email[record.email] = record.id

    def find_by_provider_subject(
        self,
        *,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> OAuthIdentityRecord | None:
        return self._by_provider_subject.get((provider, provider_user_id))

    def find_by_user_and_provider(
        self,
        *,
        user_id: str,
        provider: OAuthProvider,
    ) -> OAuthIdentityRecord | None:
        return self._by_user_provider.get((user_id, provider))

    def resolve_oauth_login(
        self,
        identity: OAuthProviderIdentity,
    ) -> tuple[str, bool]:
        existing = self.find_by_provider_subject(
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
        )
        if existing is not None:
            self._refresh_user_profile(existing.user_id, identity)
            return existing.user_id, False

        if not identity.email_verified:
            raise AuthenticationError(
                "A verified email is required to sign in with this provider"
            )

        normalized_email = _normalize_email(identity.email)
        user_id = self._ids_by_email.get(normalized_email)
        created = False
        if user_id is None:
            user_id = str(uuid4())
            created = True
            record = IdentityRecord(
                id=user_id,
                email=normalized_email,
                display_name=identity.display_name.strip() or normalized_email,
            )
            self._users_by_id[user_id] = record
            self._ids_by_email[normalized_email] = user_id
        else:
            stored = self._users_by_id[user_id]
            if identity.display_name.strip():
                self._users_by_id[user_id] = IdentityRecord(
                    id=stored.id,
                    email=stored.email,
                    display_name=identity.display_name.strip(),
                )

        linked = self.find_by_user_and_provider(
            user_id=user_id,
            provider=identity.provider,
        )
        if linked is not None:
            raise AuthenticationError(
                "This account is already linked to a different "
                "sign-in for this provider"
            )

        oauth_id = str(uuid4())
        oauth_record = OAuthIdentityRecord(
            id=oauth_id,
            user_id=user_id,
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
            provider_email=normalized_email,
        )
        key = (identity.provider, identity.provider_user_id)
        self._by_provider_subject[key] = oauth_record
        self._by_user_provider[(user_id, identity.provider)] = oauth_record
        return user_id, created

    def _refresh_user_profile(
        self,
        user_id: str,
        identity: OAuthProviderIdentity,
    ) -> None:
        stored = self._users_by_id.get(user_id)
        if stored is None:
            return
        if identity.display_name.strip():
            self._users_by_id[user_id] = IdentityRecord(
                id=stored.id,
                email=stored.email,
                display_name=identity.display_name.strip(),
            )


@dataclass(slots=True)
class SqlAlchemyOAuthIdentityStore:
    """PostgreSQL-backed OAuth identity store."""

    session_factory: SessionFactory

    def find_by_provider_subject(
        self,
        *,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> OAuthIdentityRecord | None:
        with self.session_factory() as session:
            row = self._get_by_provider_subject(session, provider, provider_user_id)
            return self._to_record(row) if row is not None else None

    def find_by_user_and_provider(
        self,
        *,
        user_id: str,
        provider: OAuthProvider,
    ) -> OAuthIdentityRecord | None:
        with self.session_factory() as session:
            row = self._get_by_user_provider(session, user_id, provider)
            return self._to_record(row) if row is not None else None

    def resolve_oauth_login(
        self,
        identity: OAuthProviderIdentity,
    ) -> tuple[str, bool]:
        if not identity.email_verified:
            raise AuthenticationError(
                "A verified email is required to sign in with this provider"
            )

        normalized_email = _normalize_email(identity.email)
        with self.session_factory() as session:
            existing = self._get_by_provider_subject(
                session,
                identity.provider,
                identity.provider_user_id,
            )
            if existing is not None:
                self._maybe_update_profiles(session, existing, identity)
                session.commit()
                return existing.user_id, False

            user = self._get_user_by_email(session, normalized_email)
            created = False
            if user is None:
                user = UserOrm(
                    id=str(uuid4()),
                    email=normalized_email,
                    display_name=identity.display_name.strip() or normalized_email,
                    password_hash=None,
                )
                session.add(user)
                created = True
            elif identity.display_name.strip():
                user.display_name = identity.display_name.strip()

            linked = self._get_by_user_provider(session, user.id, identity.provider)
            if (
                linked is not None
                and linked.provider_user_id != identity.provider_user_id
            ):
                raise AuthenticationError(
                    "This account is already linked to a different "
                    "sign-in for this provider"
                )

            if linked is None:
                session.add(
                    OAuthIdentityOrm(
                        id=str(uuid4()),
                        user_id=user.id,
                        provider=identity.provider,
                        provider_user_id=identity.provider_user_id,
                        provider_email=normalized_email,
                    )
                )

            session.commit()
            return user.id, created

    @staticmethod
    def _get_by_provider_subject(
        session: Session,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> OAuthIdentityOrm | None:
        stmt = select(OAuthIdentityOrm).where(
            OAuthIdentityOrm.provider == provider,
            OAuthIdentityOrm.provider_user_id == provider_user_id,
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _get_by_user_provider(
        session: Session,
        user_id: str,
        provider: OAuthProvider,
    ) -> OAuthIdentityOrm | None:
        stmt = select(OAuthIdentityOrm).where(
            OAuthIdentityOrm.user_id == user_id,
            OAuthIdentityOrm.provider == provider,
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _get_user_by_email(session: Session, email: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.email == email)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _to_record(row: OAuthIdentityOrm) -> OAuthIdentityRecord:
        return OAuthIdentityRecord(
            id=row.id,
            user_id=row.user_id,
            provider=row.provider,  # type: ignore[arg-type]
            provider_user_id=row.provider_user_id,
            provider_email=row.provider_email,
        )

    @staticmethod
    def _maybe_update_profiles(
        session: Session,
        existing: OAuthIdentityOrm,
        identity: OAuthProviderIdentity,
    ) -> None:
        user = session.get(UserOrm, existing.user_id)
        if user is None:
            return
        if identity.display_name.strip():
            user.display_name = identity.display_name.strip()
        normalized_email = _normalize_email(identity.email)
        existing.provider_email = normalized_email
