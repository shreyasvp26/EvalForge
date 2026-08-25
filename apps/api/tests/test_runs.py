"""Run API tests — Application services mocked."""

from __future__ import annotations

from agent_eval_application.commands.run import CancelRunCommand, CreateRunCommand


def test_create_run(client, services, auth_headers) -> None:
    payload = {
        "project_id": "proj-1",
        "case_id": "case-1",
        "case_version_id": "cv-1",
        "prompt_version_id": "pv-1",
        "agent_id": "agent-1",
        "agent_version_id": "av-1",
        "adapter_version_id": "adv-1",
        "grader_version_refs": [{"grader_id": "g-1", "grader_version_id": "gv-1"}],
        "platform_version_id": "plat-1",
    }
    response = client.post(
        "/v1/runs",
        json=payload,
        headers={**auth_headers, "Idempotency-Key": "run-key"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    cmd = services.create_run.execute.call_args.args[0]
    assert isinstance(cmd, CreateRunCommand)
    assert cmd.grader_version_refs == (("g-1", "gv-1"),)
    assert cmd.idempotency_key == "run-key"


def test_get_run(client, auth_headers) -> None:
    response = client.get("/v1/runs/run-1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == "run-1"


def test_list_runs(client, auth_headers) -> None:
    response = client.get(
        "/v1/runs",
        params={"project_id": "proj-1"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_cancel_run(client, services, auth_headers) -> None:
    response = client.post(
        "/v1/runs/run-1/cancel",
        json={"reason": "user"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    cmd = services.cancel_run.execute.call_args.args[0]
    assert isinstance(cmd, CancelRunCommand)
    assert cmd.reason == "user"


def test_list_run_events(client, services, auth_headers) -> None:
    response = client.get("/v1/runs/run-1/events", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == "evt-1"
    services.get_run_events.execute.assert_called_once()


def test_list_run_artifacts(client, services, auth_headers) -> None:
    response = client.get("/v1/runs/run-1/artifacts", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["storage_key"] == "runs/run-1/art-1"


def test_download_run_artifact(client, services, auth_headers, container) -> None:
    container.infrastructure.object_storage.get.return_value = b"artifact-bytes"
    response = client.get(
        "/v1/runs/run-1/artifacts/art-1/content",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.content == b"artifact-bytes"
    container.infrastructure.object_storage.get.assert_called_once()


def test_list_run_scores(client, services, auth_headers) -> None:
    response = client.get("/v1/runs/run-1/scores", headers=auth_headers)
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["grader_id"] == "g-1"
    assert item["value"]["detail"]["reason"] == "expected files present"
