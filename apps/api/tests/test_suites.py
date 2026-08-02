"""Suite endpoint tests — Application services mocked."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from agent_eval_application.dto.suite import (
    SuiteCompositionEntryDTO,
    SuiteVersionDTO,
)


def test_create_suite(client, services, auth_headers) -> None:
    response = client.post(
        "/v1/suites",
        json={"project_id": "proj-1", "name": "Suite A"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["id"] == "suite-1"
    services.create_suite.execute.assert_called_once()


def test_list_suites(client, auth_headers) -> None:
    response = client.get(
        "/v1/suites",
        params={"project_id": "proj-1"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == "suite-1"


def test_get_suite(client, auth_headers) -> None:
    response = client.get("/v1/suites/suite-1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Suite A"


def test_create_suite_draft_version(client, services, auth_headers) -> None:
    version = SuiteVersionDTO(
        id="sv-1",
        suite_id="suite-1",
        version_number=1,
        status="draft",
        composition=(
            SuiteCompositionEntryDTO(
                case_version_id="cv-1",
                position=0,
                case_project_id="proj-1",
            ),
        ),
        predecessor_version_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    services.create_suite_draft_version.execute.return_value = version
    response = client.post(
        "/v1/suites/suite-1/versions",
        json={
            "composition": [
                {
                    "case_version_id": "cv-1",
                    "position": 0,
                    "case_project_id": "proj-1",
                }
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["id"] == "sv-1"


def test_publish_and_retire_suite_version(client, services, auth_headers) -> None:
    version = SuiteVersionDTO(
        id="sv-1",
        suite_id="suite-1",
        version_number=1,
        status="published",
        composition=(),
        predecessor_version_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    services.publish_suite_version.execute.return_value = version
    services.retire_suite_version.execute.return_value = MagicMock(
        **{
            "id": "sv-1",
            "suite_id": "suite-1",
            "version_number": 1,
            "status": "retired",
            "composition": (),
            "predecessor_version_id": None,
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        }
    )
    # Use real DTO for retire to satisfy response_model
    retired = SuiteVersionDTO(
        id="sv-1",
        suite_id="suite-1",
        version_number=1,
        status="retired",
        composition=(),
        predecessor_version_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    services.retire_suite_version.execute.return_value = retired

    pub = client.post("/v1/suites/suite-1/versions/sv-1/publish", headers=auth_headers)
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    ret = client.post("/v1/suites/suite-1/versions/sv-1/retire", headers=auth_headers)
    assert ret.status_code == 200
    assert ret.json()["status"] == "retired"
