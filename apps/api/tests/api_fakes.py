"""Test fakes — mocked Application services; no live database."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.dto.run import (
    ArtifactDTO,
    ExecutionEventDTO,
    RunDTO,
    RunPinsDTO,
    ScoreDTO,
    ScoreValueDTO,
)
from agent_eval_application.dto.suite import SuiteDTO
from agent_eval_application.dto.user import UserDTO
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


def sample_event(**overrides: Any) -> ExecutionEventDTO:
    base = dict(
        id="evt-1",
        run_id="run-1",
        sequence=1,
        kind="message",
        action={"kind": "message", "role": "assistant", "content_summary": "hi"},
        artifact_ids=(),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        metadata={},
    )
    base.update(overrides)
    return ExecutionEventDTO(**base)


def sample_artifact(**overrides: Any) -> ArtifactDTO:
    base = dict(
        id="art-1",
        run_id="run-1",
        kind="log",
        storage_key="runs/run-1/art-1",
        content_type="text/plain",
        size_bytes=12,
        checksum="abc",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        produced_by_grader_version_id=None,
    )
    base.update(overrides)
    return ArtifactDTO(**base)


def sample_score(**overrides: Any) -> ScoreDTO:
    base = dict(
        id="score-1",
        grader_id="g-1",
        grader_version_id="gv-1",
        value=ScoreValueDTO(
            numeric=1.0,
            categorical=None,
            passed=True,
            detail={"reason": "expected files present"},
        ),
        explanation_artifact_id=None,
    )
    base.update(overrides)
    return ScoreDTO(**base)


def sample_user(**overrides: Any) -> UserDTO:
    base = dict(
        id="user-1",
        email="admin@evalforge.local",
        display_name="EvalForge Admin",
    )
    base.update(overrides)
    return UserDTO(**base)


def mock_services() -> MagicMock:
    """ApplicationServices stand-in with Magics for every public use case."""
    services = MagicMock()
    services.login.execute.return_value = sample_user()
    services.get_current_user.execute.return_value = sample_user()
    services.create_project.execute.return_value = sample_project()
    services.get_project.execute.return_value = sample_project()
    services.list_projects.execute.return_value = [sample_project()]
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
    services.create_suite_runs.execute.return_value = MagicMock()
    services.aggregate_suite_results.execute.return_value = MagicMock()

    services.create_run.execute.return_value = sample_run()
    services.get_run.execute.return_value = sample_run()
    services.list_runs_by_project.execute.return_value = [sample_run()]
    services.cancel_run.execute.return_value = sample_run(
        status="cancelled", cancellation_reason="user"
    )
    services.get_run_events.execute.return_value = [sample_event()]
    services.get_run_artifacts.execute.return_value = [sample_artifact()]
    services.get_run_scores.execute.return_value = [sample_score()]
    services.get_run_provenance.execute.return_value = MagicMock()

    # Remaining use cases return Magics; individual tests override as needed.
    return services


class FakeContainer:
    """Minimal ApiContainer stand-in for TestClient (no Infrastructure)."""

    def __init__(self, services: MagicMock, settings: Any) -> None:
        self.services = services
        self.settings = settings
        self.auth = MagicMock()
        self.memberships = MagicMock()
        self.identity = MagicMock()
        self.infrastructure = MagicMock()
        self.infrastructure.redis = None
        self.infrastructure.run_queue = MagicMock()
        self._ready = True

    def dispose(self) -> None:
        return None

    def readiness_checks(self) -> dict[str, str]:
        if not self._ready:
            return {"composition": "ok", "database": "unavailable"}
        return {"composition": "ok", "database": "ok"}


# Re-export error types for tests
__all__ = [
    "Actor",
    "ApplicationValidationError",
    "AuthorizationError",
    "FakeContainer",
    "NotFoundApplicationError",
    "mock_services",
    "sample_artifact",
    "sample_event",
    "sample_project",
    "sample_run",
    "sample_score",
    "sample_suite",
    "sample_user",
]
