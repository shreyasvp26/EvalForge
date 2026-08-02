"""Application auth use-case tests."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.auth import LoginCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import AuthenticationError
from agent_eval_application.queries.queries import GetCurrentUserQuery
from agent_eval_application.use_cases.auth import GetCurrentUser, Login
from agent_eval_infrastructure.auth import InMemoryIdentityStore


@pytest.fixture
def identity() -> InMemoryIdentityStore:
    store = InMemoryIdentityStore()
    store.upsert(
        email="ada@evalforge.local",
        password="correct-horse",
        display_name="Ada Lovelace",
        user_id="user-ada",
    )
    return store


def test_login_success(identity: InMemoryIdentityStore) -> None:
    result = Login(identity).execute(
        LoginCommand(email="Ada@EvalForge.local", password="correct-horse")
    )
    assert result.id == "user-ada"
    assert result.email == "ada@evalforge.local"
    assert result.display_name == "Ada Lovelace"


def test_login_rejects_bad_password(identity: InMemoryIdentityStore) -> None:
    with pytest.raises(AuthenticationError):
        Login(identity).execute(
            LoginCommand(email="ada@evalforge.local", password="nope")
        )


def test_get_current_user(identity: InMemoryIdentityStore) -> None:
    result = GetCurrentUser(identity).execute(
        GetCurrentUserQuery(actor=Actor(id="user-ada"))
    )
    assert result.email == "ada@evalforge.local"


def test_get_current_user_unknown(identity: InMemoryIdentityStore) -> None:
    with pytest.raises(AuthenticationError):
        GetCurrentUser(identity).execute(GetCurrentUserQuery(actor=Actor(id="missing")))
