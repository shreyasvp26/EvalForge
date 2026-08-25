"""GitHub OAuth identity parsing tests."""

from __future__ import annotations

from agent_eval_api.auth.oauth.providers.github import _select_verified_github_email


def test_select_primary_verified_email() -> None:
    emails = [
        {
            "email": "private@users.noreply.github.com",
            "verified": True,
            "primary": False,
        },
        {"email": "user@example.com", "verified": True, "primary": True},
    ]
    email, verified = _select_verified_github_email(emails)
    assert email == "user@example.com"
    assert verified is True


def test_select_first_verified_when_no_primary() -> None:
    emails = [
        {"email": "a@example.com", "verified": False},
        {"email": "b@example.com", "verified": True, "primary": False},
    ]
    email, verified = _select_verified_github_email(emails)
    assert email == "b@example.com"
    assert verified is True


def test_missing_verified_email() -> None:
    emails = [{"email": "a@example.com", "verified": False}]
    email, verified = _select_verified_github_email(emails)
    assert email == ""
    assert verified is False
