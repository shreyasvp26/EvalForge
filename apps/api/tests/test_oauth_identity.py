"""OAuth identity resolution and account linking tests."""

from __future__ import annotations

import pytest
from agent_eval_application.errors import AuthenticationError
from agent_eval_application.ports.identity import IdentityRecord
from agent_eval_application.ports.oauth_identity import OAuthProviderIdentity
from agent_eval_infrastructure.auth.oauth_identity import InMemoryOAuthIdentityStore


@pytest.fixture
def store() -> InMemoryOAuthIdentityStore:
    return InMemoryOAuthIdentityStore()


def _google_identity(**overrides: object) -> OAuthProviderIdentity:
    base = dict(
        provider="google",
        provider_user_id="google-subject-1",
        email="user@example.com",
        email_verified=True,
        display_name="Example User",
    )
    base.update(overrides)
    return OAuthProviderIdentity(**base)  # type: ignore[arg-type]


def test_resolve_creates_user_and_oauth_identity(
    store: InMemoryOAuthIdentityStore,
) -> None:
    user_id, created = store.resolve_oauth_login(_google_identity())
    assert created is True
    assert user_id
    linked = store.find_by_provider_subject(
        provider="google",
        provider_user_id="google-subject-1",
    )
    assert linked is not None
    assert linked.user_id == user_id


def test_resolve_returns_existing_provider_identity(
    store: InMemoryOAuthIdentityStore,
) -> None:
    first_id, _ = store.resolve_oauth_login(_google_identity())
    second_id, created = store.resolve_oauth_login(
        _google_identity(display_name="Updated")
    )
    assert created is False
    assert second_id == first_id


def test_links_verified_email_to_existing_user(
    store: InMemoryOAuthIdentityStore,
) -> None:
    store.seed_user(
        IdentityRecord(
            id="user-1", email="user@example.com", display_name="Password User"
        )
    )
    user_id, created = store.resolve_oauth_login(_google_identity())
    assert created is False
    assert user_id == "user-1"


def test_rejects_unverified_email(store: InMemoryOAuthIdentityStore) -> None:
    with pytest.raises(AuthenticationError, match="verified email"):
        store.resolve_oauth_login(_google_identity(email_verified=False))


def test_rejects_duplicate_provider_for_same_user(
    store: InMemoryOAuthIdentityStore,
) -> None:
    store.seed_user(
        IdentityRecord(
            id="user-1", email="user@example.com", display_name="Password User"
        )
    )
    store.resolve_oauth_login(_google_identity())
    with pytest.raises(AuthenticationError, match="already linked"):
        store.resolve_oauth_login(_google_identity(provider_user_id="google-subject-2"))
