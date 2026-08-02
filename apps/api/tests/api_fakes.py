"""Test fakes — mocked Application services; no live database."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.dto.run import RunDTO, RunPinsDTO
from agent_eval_application.dto.suite import SuiteDTO
from agent_eval_application.errors import (
    ApplicationValidationError,
    AuthorizationError,
    NotFoundApplicationError,
)


def sample_project(**overrides: Any) -> ProjectDTO:
    base = dict(
        id="proj-1",
        name="Demo",
        description="",
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        settings={},
    )
    base.update(overrides)
    return ProjectDTO(**base)


def sample_suite(**overrides: Any) -> SuiteDTO:
    base = dict(
        id="suite-1",
        project_id="proj-1",
        name="Suite A",
        description="",
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        active_version_id=None,
        versions=(),
    )
    base.update(overrides)
    return SuiteDTO(**base)


def sample_run(**overrides: Any) -> RunDTO:
    pins = RunPinsDTO(
        project_id="proj-1",
        case_version_id="cv-1",
        prompt_version_id="pv-1",
        agent_version_id="av-1",
        adapter_version_id="adv-1",
        platform_version_id="plat-1",
        grader_version_ids=("gv-1",),
        suite_version_id=None,
    )
    base = dict(
        id="run-1",
        status="queued",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        pins=pins,
        failure_reason=None,
        cancellation_reason=None,
        sandbox_id=None,
        expected_grader_count=1,
        produced_score_count=0,
        is_partially_graded=False,
        scores=(),
    )
    base.update(overrides)
    return RunDTO(**base)


def mock_services() -> MagicMock:
    """ApplicationServices stand-in with Magics for every public use case."""
    services = MagicMock()
    services.create_project.execute.return_value = sample_project()
    services.get_project.execute.return_value = sample_project()
    services.rename_project.execute.return_value = sample_project(name="Renamed")
    services.update_project_settings.execute.return_value = sample_project(
        settings={"k": "v"}
    )
    services.deprecate_project.execute.return_value = sample_project(
        status="deprecated"
    )

    services.create_suite.execute.return_value = sample_suite()
    services.get_suite.execute.return_value = sample_suite()
    services.list_suites_by_project.execute.return_value = [sample_suite()]
    services.create_suite_draft_version.execute.return_value = MagicMock()
    services.publish_suite_version.execute.return_value = MagicMock()
    services.retire_suite_version.execute.return_value = MagicMock()
    services.deprecate_suite.execute.return_value = sample_suite(status="deprecated")

    services.create_run.execute.return_value = sample_run()
    services.get_run.execute.return_value = sample_run()
    services.list_runs_by_project.execute.return_value = [sample_run()]
    services.cancel_run.execute.return_value = sample_run(
        status="cancelled", cancellation_reason="user"
    )

    # Remaining use cases return Magics; individual tests override as needed.
    return services


class FakeContainer:
    """Minimal ApiContainer stand-in for TestClient (no Infrastructure)."""

    def __init__(self, services: MagicMock, settings: Any) -> None:
        self.services = services
        self.settings = settings
        self.auth = MagicMock()
        self.infrastructure = MagicMock()
        self.infrastructure.engine.connect.return_value.__enter__ = MagicMock(
            return_value=MagicMock()
        )
        self.infrastructure.engine.connect.return_value.__exit__ = MagicMock(
            return_value=False
        )

    def dispose(self) -> None:
        return None

    def readiness_checks(self) -> dict[str, str]:
        return {"composition": "ok", "database": "ok"}


# Re-export error types for tests
__all__ = [
    "Actor",
    "ApplicationValidationError",
    "AuthorizationError",
    "FakeContainer",
    "NotFoundApplicationError",
    "mock_services",
    "sample_project",
    "sample_run",
    "sample_suite",
]
