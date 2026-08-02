"""Production end-to-end execution pipeline tests.

Uses real DockerSandbox (FakeDockerEngine), ClaudeCodeAdapter, objective +
rubric graders, and Application use cases. Mocks ONLY MockJudgeProvider.
"""

from __future__ import annotations

import json

import pytest
from agent_eval_application.commands.grader import (
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, GetRunScoresQuery
from agent_eval_application.use_cases.grader import (
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.run import CreateRun, GetRun, GetRunScores
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import (
    BuildSuccessGrader,
    DiffValidationGrader,
    ExpectedFileGrader,
    TestPassGrader,
)
from agent_eval_graders.rubric import (
    MockJudgeProvider,
    RubricGrader,
    RubricSpecification,
)
from agent_eval_workers.clock import FakeClock
from agent_eval_workers.execution_engine import (
    EngineOutcomeKind,
)
from agent_eval_workers.integration.composition import (
    build_production_harness,
    rebuild_production_worker,
)
from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.worker import WorkerState
from docker_fakes import FakeDockerEngine

pytest_plugins = ["test_run_use_cases"]


@pytest.fixture
def prod_world(world):
    """Extend Application world with three published versions of the Case grader."""
    uow, ids, auth, events, actor = (
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["actor"],
    )
    grader_id = world["grader_id"]
    refs: list[tuple[str, str]] = [(grader_id, world["grader_version_id"])]
    for label in ("v-diff", "v-rubric"):
        gv = CreateGraderDraftVersion(uow, ids, auth, events).execute(
            CreateGraderDraftVersionCommand(
                actor=actor,
                grader_id=grader_id,
                label=label,
                specification=label,
            )
        )
        gv = PublishGraderVersion(uow, auth, events).execute(
            PublishGraderVersionCommand(
                actor=actor, grader_id=grader_id, version_id=gv.id
            )
        )
        refs.append((grader_id, gv.id))
    world["grader_refs"] = tuple(refs)
    world["files_grader"] = refs[0]
    world["diff_grader"] = refs[1]
    world["rubric_grader"] = refs[2]
    return world


def _create_queued_run(world, *, grader_refs=None):
    refs = grader_refs or world["grader_refs"]
    return CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            case_id=world["case_id"],
            case_version_id=world["case_version_id"],
            prompt_version_id=world["prompt_version_id"],
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            grader_version_refs=tuple(refs),
            platform_version_id="platform-v1",
        )
    )


def _default_specs(world) -> tuple[GraderInvocationSpec, ...]:
    files_id, files_vid = world["files_grader"]
    diff_id, diff_vid = world["diff_grader"]
    rubric_id, rubric_vid = world["rubric_grader"]
    rubric = RubricSpecification(
        title="Quality",
        instructions="Score correctness",
        pass_threshold=0.5,
    )
    body = json.dumps({"numeric": 0.9, "passed": True, "reason": "solid work"})
    return (
        GraderInvocationSpec(
            name="expected_file",
            grader_id=files_id,
            grader_version_id=files_vid,
            factory=lambda: ExpectedFileGrader(expected_paths=("main.py",)),
            specification="main.py",
        ),
        GraderInvocationSpec(
            name="diff_validation",
            grader_id=diff_id,
            grader_version_id=diff_vid,
            factory=lambda: DiffValidationGrader(),
            specification="diff",
        ),
        GraderInvocationSpec(
            name="rubric",
            grader_id=rubric_id,
            grader_version_id=rubric_vid,
            factory=lambda: RubricGrader(
                rubric=rubric,
                provider=MockJudgeProvider(response=body),
            ),
            specification=rubric.instructions,
        ),
    )


def _harness(world, **kwargs):
    from agent_eval_adapters.sdk.models import RunMetadata

    return build_production_harness(
        docker_engine=kwargs.pop("docker_engine", FakeDockerEngine()),
        uow_factory=world["uow"],
        ids=world["ids"],
        auth=world["auth"],
        events=world["events"],
        actor=Actor(id="system-worker"),
        grader_specs=kwargs.pop("grader_specs", _default_specs(world)),
        run_metadata_factory=lambda rid: RunMetadata(
            run_id=rid.value,
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            prompt_version_id=world["prompt_version_id"],
            case_version_id=world["case_version_id"],
        ),
        **kwargs,
    )


def test_successful_execution_end_to_end(prod_world) -> None:
    run = _create_queued_run(prod_world)
    harness = _harness(prod_world)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert result.phase is OrchestrationPhase.COMPLETED
    assert harness.sandbox.provisioned == [RunId(run.id)]
    assert harness.adapter.started and harness.adapter.ran and harness.adapter.finished
    assert harness.status.running == [RunId(run.id)]
    assert harness.status.grading == [RunId(run.id)]
    assert harness.status.completed == [RunId(run.id)]
    assert harness.grading.scheduled == [RunId(run.id)]
    assert len(harness.grading.scores) == 3

    dto = GetRun(prod_world["uow"], prod_world["auth"]).execute(
        GetRunQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert dto.status == "completed"
    assert dto.produced_score_count == 3
    scores = GetRunScores(prod_world["uow"], prod_world["auth"]).execute(
        GetRunScoresQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert len(scores) == 3
    assert all(s.value.passed is True for s in scores)


def test_build_failure_grading(prod_world) -> None:
    """Objective BuildSuccessGrader fails when no build signal is recorded."""
    files_id, files_vid = prod_world["files_grader"]
    specs = (
        GraderInvocationSpec(
            name="build",
            grader_id=files_id,
            grader_version_id=files_vid,
            factory=lambda: BuildSuccessGrader(),
            specification="build",
        ),
    )
    run = _create_queued_run(prod_world, grader_refs=((files_id, files_vid),))
    harness = _harness(prod_world, grader_specs=specs)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    scores = GetRunScores(prod_world["uow"], prod_world["auth"]).execute(
        GetRunScoresQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert len(scores) == 1
    assert scores[0].value.passed is False


def test_test_failure_grading(prod_world) -> None:
    files_id, files_vid = prod_world["files_grader"]
    specs = (
        GraderInvocationSpec(
            name="tests",
            grader_id=files_id,
            grader_version_id=files_vid,
            factory=lambda: TestPassGrader(),
            specification="pytest",
        ),
    )
    run = _create_queued_run(prod_world, grader_refs=((files_id, files_vid),))
    harness = _harness(prod_world, grader_specs=specs)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    scores = GetRunScores(prod_world["uow"], prod_world["auth"]).execute(
        GetRunScoresQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert scores[0].value.passed is False


def test_timeout(prod_world) -> None:
    clock = FakeClock()
    harness = _harness(
        prod_world,
        clock=clock,
        execution_timeout_seconds=1.0,
    )

    def slow(_run_id: RunId) -> None:
        clock.advance(5.0)

    harness.sandbox.after_provision = slow
    run = _create_queued_run(prod_world)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.TIMEOUT


def test_cancellation(prod_world) -> None:
    harness = _harness(prod_world)
    run = _create_queued_run(prod_world)
    harness.enqueue(run.id)
    harness.cancellation.request_cancel(RunId(run.id))
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.CANCELLED
    assert harness.status.cancelled == [RunId(run.id)]
    assert harness.sandbox.destroyed


def test_sandbox_failure(prod_world) -> None:
    harness = _harness(prod_world, fail_sandbox=True, max_attempts=2)
    run = _create_queued_run(prod_world)
    harness.enqueue(run.id)
    first = harness.worker.run_once(block=False)
    assert first is not None
    assert first.kind is EngineOutcomeKind.RECOVERABLE_FAILURE
    assert first.failure_cause is FailureCause.SANDBOX_FAILURE
    second = harness.worker.run_once(block=False)
    assert second is not None
    assert second.kind is EngineOutcomeKind.FAILED
    assert harness.status.failed[-1][1] is FailureCause.SANDBOX_FAILURE


def test_adapter_failure(prod_world) -> None:
    harness = _harness(prod_world, fail_adapter=True)
    run = _create_queued_run(prod_world)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.ADAPTER_FAILURE
    assert harness.sandbox.destroyed


def test_partial_grading(prod_world) -> None:
    files_id, files_vid = prod_world["files_grader"]
    diff_id, diff_vid = prod_world["diff_grader"]
    rubric_id, rubric_vid = prod_world["rubric_grader"]

    def boom() -> ExpectedFileGrader:
        class Boom(ExpectedFileGrader):
            def grade(self, context, events, artifacts):
                raise RuntimeError("grader boom")

        return Boom(expected_paths=("main.py",))

    specs = (
        GraderInvocationSpec(
            name="boom",
            grader_id=files_id,
            grader_version_id=files_vid,
            factory=boom,
        ),
        GraderInvocationSpec(
            name="ok-files",
            grader_id=diff_id,
            grader_version_id=diff_vid,
            factory=lambda: ExpectedFileGrader(expected_paths=("main.py",)),
        ),
        GraderInvocationSpec(
            name="rubric",
            grader_id=rubric_id,
            grader_version_id=rubric_vid,
            factory=lambda: RubricGrader(
                rubric=RubricSpecification(
                    title="Q", instructions="ok", pass_threshold=0.5
                ),
                provider=MockJudgeProvider(
                    response='{"numeric": 1.0, "passed": true, "reason": "ok"}'
                ),
            ),
        ),
    )
    run = _create_queued_run(prod_world)
    harness = _harness(prod_world, grader_specs=specs)
    harness.enqueue(run.id)
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert len(harness.grading.scores) == 2
    assert harness.grading.failures
    dto = GetRun(prod_world["uow"], prod_world["auth"]).execute(
        GetRunQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert dto.is_partially_graded is True


def test_checkpoint_recovery(prod_world) -> None:
    harness = _harness(prod_world)
    run = _create_queued_run(prod_world)
    harness.enqueue(run.id)

    def stop_on_start(_run_id: RunId) -> None:
        harness.worker.request_stop()

    harness.adapter.after_start = stop_on_start
    interrupted = harness.worker.run_once(block=False)
    assert interrupted is not None
    assert interrupted.kind is EngineOutcomeKind.INTERRUPTED
    assert harness.worker.state is WorkerState.STOPPED

    worker2 = rebuild_production_worker(harness)
    resumed = worker2.run_once(block=False)
    assert resumed is not None
    assert resumed.kind is EngineOutcomeKind.COMPLETED
    assert harness.status.completed == [RunId(run.id)]


def test_exactly_once_event_persistence(prod_world) -> None:
    """Duplicate Application writes while Running must not append a second Event.

    Domain accepts Execution Events only in Running; replay after Completed is
    rejected by phase rules. Idempotency is verified mid-pipeline.
    """
    from agent_eval_application.queries.queries import GetRunEventsQuery
    from agent_eval_application.use_cases.run import GetRunEvents

    run = _create_queued_run(prod_world)
    harness = _harness(prod_world, batch_size=1)
    replays: list[bool] = []
    inner_writer = harness.pipeline.writer

    class _ReplayWriter:
        def record_execution_event(self, command):
            dto = inner_writer.record_execution_event(command)
            if not replays:
                again = inner_writer.record_execution_event(command)
                assert again.already_recorded is True
                assert again.id == dto.id
                assert again.sequence == dto.sequence
                replays.append(True)
            return dto

        def record_artifact(self, command):
            return inner_writer.record_artifact(command)

    harness.pipeline.writer = _ReplayWriter()  # type: ignore[assignment]
    harness.enqueue(run.id)
    harness.worker.run_once(block=False)
    assert replays

    events = GetRunEvents(prod_world["uow"], prod_world["auth"]).execute(
        GetRunEventsQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert len(events) >= 1
    assert len({e.id for e in events}) == len(events)


def test_score_persistence_and_run_completion(prod_world) -> None:
    run = _create_queued_run(prod_world)
    harness = _harness(prod_world)
    harness.enqueue(run.id)
    harness.worker.run_once(block=False)
    dto = GetRun(prod_world["uow"], prod_world["auth"]).execute(
        GetRunQuery(actor=prod_world["actor"], run_id=run.id)
    )
    assert dto.status == "completed"
    assert dto.produced_score_count == dto.expected_grader_count
    assert harness.grading.scores
    assert all(s.score.run_id.value == run.id for s in harness.grading.scores)
