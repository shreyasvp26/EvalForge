"""Provider catalog + BYOK connection API tests."""

from __future__ import annotations

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import NotFoundApplicationError
from agent_eval_application.use_cases.provider_connections import (
    CreateProviderConnection,
    CreateProviderConnectionCommand,
    ListProviderConnections,
    ListProviderConnectionsQuery,
    RevokeProviderConnection,
    RevokeProviderConnectionCommand,
)
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.execution.provider_connection import ProviderConnectionStatus
from agent_eval_infrastructure.auth import InMemoryProviderConnectionStore
from agent_eval_infrastructure.secrets.fernet_box import _derive_fernet_key


@pytest.fixture
def provider_secret_key(monkeypatch: pytest.MonkeyPatch) -> bytes:
    raw = "test-provider-credentials-key-32chars!!"
    monkeypatch.setenv("PROVIDER_CREDENTIALS_KEY", raw)
    return _derive_fernet_key(raw)


def test_create_connection_never_returns_secret(client, services, auth_headers) -> None:
    response = client.post(
        "/v1/provider-connections",
        json={
            "provider_key": "google",
            "api_key": "sk-secret-should-never-leak",
            "display_name": "My Google",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert "api_key" not in body
    assert "secret_ciphertext" not in body
    assert "secret" not in body
    assert body["masked_key"].startswith("••••")
    assert "sk-secret" not in str(body)
    cmd = services.create_provider_connection.execute.call_args.args[0]
    assert cmd.provider_key == "google"
    assert cmd.api_key == "sk-secret-should-never-leak"
    assert cmd.actor.id == "actor-1"


def test_list_connections(client, auth_headers) -> None:
    response = client.get("/v1/provider-connections", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    item = body["items"][0]
    assert item["id"] == "conn-1"
    assert item["provider_key"] == "google"
    assert "api_key" not in item
    assert "secret_ciphertext" not in item
    assert item["masked_key"].startswith("••••")


def test_revoke_connection(client, services, auth_headers) -> None:
    response = client.delete(
        "/v1/provider-connections/conn-1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    cmd = services.revoke_provider_connection.execute.call_args.args[0]
    assert cmd.connection_id == "conn-1"
    assert cmd.actor.id == "actor-1"


def test_list_providers(client, auth_headers) -> None:
    response = client.get("/v1/providers", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    google = next(i for i in body["items"] if i["provider_key"] == "google")
    assert google["live_capable"] is True
    assert "gemini_cli" in google["supported_adapters"]


def test_list_models_filter(client, auth_headers) -> None:
    response = client.get(
        "/v1/models",
        params={"provider_key": "google"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert all(item["provider_key"] == "google" for item in body["items"])


def test_cross_user_isolation_mock_store(provider_secret_key: bytes) -> None:
    store = InMemoryProviderConnectionStore(secret_key=provider_secret_key)
    create = CreateProviderConnection(store)
    list_uc = ListProviderConnections(store)
    revoke = RevokeProviderConnection(store)

    alice = Actor(id="alice")
    bob = Actor(id="bob")

    alice_conn = create.execute(
        CreateProviderConnectionCommand(
            actor=alice,
            provider_key="google",
            api_key="alice-secret-key-value",
            display_name="Alice Google",
        )
    )
    assert alice_conn.status is ProviderConnectionStatus.ACTIVE
    public = alice_conn.to_public_dict()
    assert "api_key" not in public
    assert "secret_ciphertext" not in public
    assert "alice-secret" not in str(public)

    bob_list = list_uc.execute(ListProviderConnectionsQuery(actor=bob))
    assert bob_list == []

    alice_list = list_uc.execute(ListProviderConnectionsQuery(actor=alice))
    assert len(alice_list) == 1
    assert alice_list[0].id == alice_conn.id

    with pytest.raises(NotFoundError):
        store.get_for_user(user_id=bob.id, connection_id=alice_conn.id)

    with pytest.raises(NotFoundApplicationError):
        revoke.execute(
            RevokeProviderConnectionCommand(actor=bob, connection_id=alice_conn.id)
        )

    revoked = revoke.execute(
        RevokeProviderConnectionCommand(actor=alice, connection_id=alice_conn.id)
    )
    assert revoked.status is ProviderConnectionStatus.REVOKED
