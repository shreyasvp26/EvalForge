"""Additional CRUD endpoint smoke tests (cases, agents, adapters, graders)."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_eval_application.dto.agent import AdapterDTO, AgentDTO
from agent_eval_application.dto.case import CaseDTO
from agent_eval_application.dto.grader import GraderDTO


def test_create_and_get_case(client, services, auth_headers) -> None:
    case = CaseDTO(
        id="case-1",
        project_id="proj-1",
        prompt_id="prompt-1",
        name="Case",
        description="",
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        active_version_id=None,
        active_prompt_version_id=None,
        versions=(),
        prompt_versions=(),
    )
    services.create_case.execute.return_value = case
    services.get_case.execute.return_value = case
    services.list_cases_by_project.execute.return_value = [case]

    created = client.post(
        "/v1/cases",
        json={"project_id": "proj-1", "name": "Case"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["id"] == "case-1"

    listed = client.get(
        "/v1/cases", params={"project_id": "proj-1"}, headers=auth_headers
    )
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    got = client.get("/v1/cases/case-1", headers=auth_headers)
    assert got.status_code == 200


def test_create_prompt_draft(client, services, auth_headers) -> None:
    from agent_eval_application.dto.case import PromptVersionDTO

    version = PromptVersionDTO(
        id="pv-1",
        prompt_id="prompt-1",
        version_number=1,
        status="draft",
        content="fix the bug",
        predecessor_version_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    services.create_prompt_draft_version.execute.return_value = version
    response = client.post(
        "/v1/cases/case-1/prompts/versions",
        json={"content": "fix the bug"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["content"] == "fix the bug"


def test_create_and_get_agent(client, services, auth_headers) -> None:
    agent = AgentDTO(
        id="agent-1",
        name="Claude",
        description="",
        adapter_id=None,
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        active_version_id=None,
        versions=(),
    )
    services.create_agent.execute.return_value = agent
    services.get_agent.execute.return_value = agent

    created = client.post(
        "/v1/agents",
        json={"name": "Claude"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    got = client.get("/v1/agents/agent-1", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Claude"


def test_create_adapter(client, services, auth_headers) -> None:
    adapter = AdapterDTO(
        id="adapter-1",
        agent_id="agent-1",
        name="claude-adapter",
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        active_version_id=None,
        versions=(),
    )
    services.create_adapter.execute.return_value = adapter
    response = client.post(
        "/v1/adapters",
        json={"agent_id": "agent-1", "name": "claude-adapter"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["agent_id"] == "agent-1"


def test_create_and_get_grader(client, services, auth_headers) -> None:
    grader = GraderDTO(
        id="grader-1",
        name="tests",
        family="objective",
        description="",
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        active_version_id=None,
        versions=(),
    )
    services.create_grader.execute.return_value = grader
    services.get_grader.execute.return_value = grader

    created = client.post(
        "/v1/graders",
        json={"name": "tests", "family": "objective"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    got = client.get("/v1/graders/grader-1", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["family"] == "objective"
