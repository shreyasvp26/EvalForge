"""JWT authentication boundary tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from agent_eval_api.auth.jwt import (
    JwtAuthenticationError,
    actor_from_access_token,
    issue_access_token,
    parse_access_token,
)
from agent_eval_api.config import ApiSettings
from agent_eval_application.common.actor import Actor


@pytest.fixture
def jwt_settings() -> ApiSettings:
    return ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="unit-test-secret-key-32bytes-min!!",
        jwt_issuer="evalforge-test",
        jwt_audience="evalforge-api",
        auth_dev_accept_bearer_as_actor_id=False,
    )


def test_issue_and_parse_roundtrip(jwt_settings: ApiSettings) -> None:
    token = issue_access_token("actor-42", jwt_settings)
    parsed = parse_access_token(token, jwt_settings)
    assert parsed.subject == "actor-42"
    actor = actor_from_access_token(token, jwt_settings)
    assert actor == Actor(id="actor-42")


def test_expired_token_rejected(jwt_settings: ApiSettings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "actor-1",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": jwt_settings.jwt_issuer,
            "aud": jwt_settings.jwt_audience,
        },
        jwt_settings.jwt_secret_key,
        algorithm=jwt_settings.jwt_algorithm,
    )
    with pytest.raises(JwtAuthenticationError, match="expired"):
        parse_access_token(token, jwt_settings)


def test_tampered_token_rejected(jwt_settings: ApiSettings) -> None:
    token = issue_access_token("actor-1", jwt_settings)
    with pytest.raises(JwtAuthenticationError):
        parse_access_token(token + "x", jwt_settings)


def test_missing_subject_rejected(jwt_settings: ApiSettings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iat": now,
            "exp": now + timedelta(hours=1),
            "iss": jwt_settings.jwt_issuer,
            "aud": jwt_settings.jwt_audience,
        },
        jwt_settings.jwt_secret_key,
        algorithm=jwt_settings.jwt_algorithm,
    )
    with pytest.raises(JwtAuthenticationError):
        parse_access_token(token, jwt_settings)


def test_api_rejects_raw_actor_id_without_jwt(client) -> None:
    response = client.get(
        "/v1/system/info",
        headers={"Authorization": "Bearer actor-1"},
    )
    assert response.status_code == 401


def test_api_accepts_valid_jwt(client, auth_headers) -> None:
    response = client.get("/v1/system/info", headers=auth_headers)
    assert response.status_code == 200


def test_health_still_unauthenticated(client) -> None:
    assert client.get("/health/live").status_code == 200


def test_settings_require_secret_without_dev_bypass() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        ApiSettings(
            environment="test",
            jwt_secret_key=None,
            auth_dev_accept_bearer_as_actor_id=False,
        )
