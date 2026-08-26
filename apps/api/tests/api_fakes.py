"""Test fakes — mocked Application services; no live database."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.dto.provenance import ReproducibilityDTO, RunProvenanceDTO
from agent_eval_application.dto.run import (
    ArtifactDTO,
    ExecutionEventDTO,
    RunDTO,
    RunPinsDTO,
    RunTelemetryDTO,
    ScoreDTO,
    ScoreValueDTO,
)
from agent_eval_application.dto.run_comparison import (
    RunComparabilityDTO,
    RunComparisonDeltaDTO,
    RunComparisonEntryDTO,
    RunComparisonResultDTO,
)
from agent_eval_application.dto.run_diagnosis import (
    RunDiagnosisDTO,
)
from agent_eval_application.dto.suite import SuiteDTO
from agent_eval_application.dto.user import UserDTO
from agent_eval_application.errors import (
    ApplicationValidationError,
    AuthorizationError,
    NotFoundApplicationError,
)
from agent_eval_application.scoring.aggregation import ScoreAggregate


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
        failure_category=None,
        cancellation_reason=None,
        sandbox_id=None,
        expected_grader_count=1,
        produced_score_count=0,
        is_partially_graded=False,
        scores=(),
        telemetry=RunTelemetryDTO.from_cost(None),
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


def sample_provenance(**overrides: Any) -> RunProvenanceDTO:
    aggregate = ScoreAggregate(
        passed=True,
        overall_score=1.0,
        objective_failed=False,
        score_count=1,
        reason="all graders reported passed=true",
    )
    base = dict(
        run_id="run-1",
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        failure_reason=None,
        failure_category=None,
        cancellation_reason=None,
        project_id="proj-1",
        case_version_id="cv-1",
        prompt_version_id="pv-1",
        agent_version_id="av-1",
        adapter_version_id="adv-1",
        platform_version_id="plat-1",
        grader_version_ids=("gv-1",),
        suite_version_id=None,
        repository_url="https://example.com/r.git",
        commit_sha="deadbeef",
        subdirectory=None,
        agent_name="Agent",
        agent_version_label="1.0",
        adapter_name="claude_code",
        adapter_version_label="1.0",
        adapter_key="claude_code",
        grader_summaries=(),
        score_aggregate=aggregate,
        expected_grader_count=1,
        produced_score_count=1,
        is_partially_graded=False,
        telemetry=RunTelemetryDTO.from_cost(None),
        event_count=0,
        artifact_count=0,
        execution_mode=None,
        execution_metadata={},
        reproducibility=ReproducibilityDTO(
            can_reproduce=True,
            missing=(),
            notes="All repository pins and version pins are present for reproduction.",
        ),
    )
    base.update(overrides)
    return RunProvenanceDTO(**base)


def sample_comparison(**overrides: Any) -> RunComparisonResultDTO:
    run = sample_run()
    aggregate = ScoreAggregate(
        passed=True,
        overall_score=1.0,
        objective_failed=False,
        score_count=1,
        reason="all graders reported passed=true",
    )
    entry = RunComparisonEntryDTO(
        run_id=run.id,
        status=run.status,
        failure_reason=run.failure_reason,
        failure_category=run.failure_category,
        pins=run.pins,
        repository_url="https://example.com/r.git",
        commit_sha="deadbeef",
        adapter_key="claude_code",
        adapter_name="claude_code",
        prompt_version="v1",
        agent_version="1.0",
        telemetry=run.telemetry,
        score_aggregate=aggregate,
        duration_ms=None,
        execution_mode=None,
        benchmark_key="|cv|pv|plat|gv|url|sha",
        suite_version_id=None,
    )
    base = dict(
        baseline_run_id=run.id,
        runs=(entry, entry),
        deltas=(
            RunComparisonDeltaDTO(
                run_id=run.id,
                score_delta=0.0,
                pass_changed=False,
                duration_delta_ms=0,
                pin_differences=(),
            ),
        ),
        comparability=RunComparabilityDTO(
            compatible=True,
            shared_dimensions=(
                "case_version_id",
                "prompt_version_id",
                "platform_version_id",
                "grader_version_ids",
                "repository_url",
                "commit_sha",
            ),
            agent_difference_dimensions=(
                "agent_version_id",
                "adapter_version_id",
                "adapter_key",
                "execution_mode",
            ),
            mismatches=(),
            expected_agent_differences=(),
            benchmark_key="|cv|pv|plat|gv|url|sha",
            notes="Runs share benchmark dimensions.",
        ),
    )
    base.update(overrides)
    return RunComparisonResultDTO(**base)


def sample_diagnosis(**overrides: Any) -> RunDiagnosisDTO:
    base = dict(
        run_id="run-1",
        status="failed",
        summary="Run failed during execution.",
        category="sandbox_failure",
        reason="sandbox died",
        evidence=("sandbox died",),
        failing_grader_reasons=(),
        last_events=(),
        relevant_artifact_ids=(),
    )
    base.update(overrides)
    return RunDiagnosisDTO(**base)


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
    services.get_run_provenance.execute.return_value = sample_provenance()
    services.compare_runs.execute.return_value = sample_comparison()
    services.diagnose_run_failure.execute.return_value = sample_diagnosis()

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
        self.oauth_identities = MagicMock()
        self.oauth = MagicMock()
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
    "sample_comparison",
    "sample_diagnosis",
    "sample_event",
    "sample_provenance",
    "sample_project",
    "sample_run",
    "sample_score",
    "sample_suite",
    "sample_user",
]
