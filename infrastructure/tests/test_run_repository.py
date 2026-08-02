"""Run repository adapter tests — append-only children and optimistic locking."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.ids import (
    ArtifactId,
    ExecutionEventId,
    GraderId,
    PlatformVersionId,
    RunId,
    SandboxId,
    ScoreId,
)
from agent_eval_domain.execution.entities import (
    ArtifactKind,
    ExecutionCost,
    ScoreValue,
)
from agent_eval_domain.execution.normalized_model import ToolCallAction
from agent_eval_domain.execution.run import EvaluationRun, RunPins
from agent_eval_domain.execution.run_status import RunStatus
from agent_eval_infrastructure.database.models.execution.run import RunOrm
from agent_eval_infrastructure.repositories import SqlAlchemyRunRepository
from sqlalchemy.orm.exc import StaleDataError

from .conftest import NOW, seed_agent_adapter, seed_case, seed_grader, seed_project


def _build_run(repos) -> tuple[EvaluationRun, GraderId]:
    project = seed_project(repos)
    grader, grader_version = seed_grader(repos)
    _, case_version, prompt_version = seed_case(
        repos, project_id=project.id, grader_id=grader.id
    )
    _, _, agent_version, adapter_version = seed_agent_adapter(repos)

    pins = RunPins(
        project_id=project.id,
        case_version_id=case_version.id,
        prompt_version_id=prompt_version.id,
        agent_version_id=agent_version.id,
        adapter_version_id=adapter_version.id,
        platform_version_id=PlatformVersionId("platform-v1"),
        grader_version_ids=(grader_version.id,),
    )
    run = EvaluationRun(
        id=RunId("run-1"),
        pins=pins,
        status=RunStatus.CREATED,
        created_at=NOW,
    )
    return run, grader.id


def test_run_save_get_update_and_list(repos) -> None:
    run, _ = _build_run(repos)
    repos["runs"].save(run)
    repos["session"].flush()

    loaded = repos["runs"].get(run.id)
    assert loaded.status is RunStatus.CREATED
    assert loaded.pins.platform_version_id.value == "platform-v1"
    assert loaded.sandbox is None

    loaded.queue()
    repos["runs"].save(loaded)
    repos["session"].flush()

    queued = repos["runs"].get(run.id)
    assert queued.status is RunStatus.QUEUED

    listed = repos["runs"].list_by_project(run.pins.project_id)
    assert [r.id for r in listed] == [run.id]


def test_run_append_only_children_and_mapping(repos) -> None:
    run, grader_id = _build_run(repos)
    run.queue()
    run.start(sandbox_id=SandboxId("sandbox-1"))
    run.store_artifact(
        artifact_id=ArtifactId("art-1"),
        kind=ArtifactKind.LOG,
        storage_key="runs/run-1/log.txt",
        content_type="text/plain",
        size_bytes=12,
        checksum="abc",
        created_at=NOW,
    )
    run.record_execution_event(
        event_id=ExecutionEventId("evt-1"),
        action=ToolCallAction(tool_name="read", arguments={"path": "a.py"}),
        occurred_at=NOW,
        artifact_ids=[ArtifactId("art-1")],
        metadata={"source": "adapter"},
    )
    run.record_cost(
        ExecutionCost(
            input_tokens=10, output_tokens=4, wall_clock_ms=100, compute_ms=80
        )
    )
    run.start_grading()
    run.record_score(
        score_id=ScoreId("score-1"),
        grader_id=grader_id,
        grader_version_id=run.pins.grader_version_ids[0],
        value=ScoreValue(passed=True, numeric=1.0),
        created_at=NOW,
    )
    repos["runs"].save(run)
    repos["session"].flush()

    loaded = repos["runs"].get(run.id)
    assert loaded.status is RunStatus.GRADING
    assert loaded.cost is not None
    assert loaded.cost.input_tokens == 10
    assert len(loaded.execution_events) == 1
    assert loaded.execution_events[0].action.tool_name == "read"  # type: ignore[union-attr]
    assert loaded.artifacts[0].storage_key == "runs/run-1/log.txt"
    assert loaded.scores[0].value.passed is True
    assert loaded.sandbox is None  # Sandbox is Domain-only (Schema Design)

    # Re-saving must not duplicate append-only children.
    repos["runs"].save(loaded)
    repos["session"].flush()
    again = repos["runs"].get(run.id)
    assert len(again.execution_events) == 1
    assert len(again.artifacts) == 1
    assert len(again.scores) == 1


def test_run_get_missing(repos) -> None:
    with pytest.raises(NotFoundError):
        repos["runs"].get(RunId("missing"))


def test_run_optimistic_locking(repos) -> None:
    run, _ = _build_run(repos)
    repos["runs"].save(run)
    repos["session"].commit()

    engine = repos["session"].get_bind()
    from agent_eval_infrastructure.database.session import create_session_factory

    factory = create_session_factory(engine)
    session_a = factory()
    session_b = factory()
    try:
        row_a = session_a.get(RunOrm, run.id.value)
        row_b = session_b.get(RunOrm, run.id.value)
        assert row_a is not None and row_b is not None
        assert row_a.lock_version == row_b.lock_version == 1

        row_a.status = RunStatus.QUEUED.value
        session_a.commit()

        row_b.status = RunStatus.RUNNING.value
        with pytest.raises(StaleDataError):
            session_b.commit()
    finally:
        session_a.close()
        session_b.close()


def test_run_repository_uses_shared_session(repos) -> None:
    assert isinstance(repos["runs"], SqlAlchemyRunRepository)
    assert repos["runs"].session is repos["session"]
