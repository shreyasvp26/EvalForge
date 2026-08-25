"""Run API tests — Application services mocked."""

from __future__ import annotations

from agent_eval_application.commands.run import CancelRunCommand, CreateRunCommand
from api_fakes import sample_artifact


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


def test_compare_runs(client, services, auth_headers) -> None:
    response = client.post(
        "/v1/runs/compare",
        json={"run_ids": ["run-1", "run-2"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_run_id"] == "run-1"
    assert len(body["runs"]) == 2
    services.compare_runs.execute.assert_called_once()


def test_diagnose_run_failure(client, services, auth_headers) -> None:
    response = client.get("/v1/runs/run-1/diagnosis", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "sandbox_failure"
    services.diagnose_run_failure.execute.assert_called_once()


def test_preview_run_artifact_truncates(
    client, services, auth_headers, container
) -> None:
    large = b"a" * (256 * 1024 + 50)
    container.infrastructure.object_storage.get.return_value = large
    response = client.get(
        "/v1/runs/run-1/artifacts/art-1/preview",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previewable"] is True
    assert body["truncated"] is True
    assert len(body["preview"]) == 256 * 1024


def test_preview_run_artifact_rejects_html(client, services, auth_headers) -> None:
    services.get_run_artifacts.execute.return_value = [
        sample_artifact(content_type="text/html")
    ]
    response = client.get(
        "/v1/runs/run-1/artifacts/art-1/preview",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previewable"] is False
    assert body["preview"] is None
