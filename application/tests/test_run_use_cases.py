"""Run creation, lifecycle, and grading orchestration tests."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAdapterVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    PublishCaseVersionCommand,
    PublishPromptVersionCommand,
)
from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.commands.run import (
    CancelRunCommand,
    CompleteRunCommand,
    CreateRunCommand,
    FailRunCommand,
    RecordArtifactCommand,
    RecordExecutionEventCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import DomainTranslationError
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
    PublishPromptVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_application.use_cases.run import (
    CancelRun,
    CompleteRun,
    CreateRun,
    FailRun,
    RecordArtifact,
    RecordExecutionEvent,
    RecordScore,
    StartGrading,
    StartRun,
)
from fakes import (
    AllowAllAuth,
    InMemoryIdempotencyStore,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    RecordingRunQueue,
    SharedStore,
)


@pytest.fixture
def world():
    """Fully published Project / Case / Agent / Adapter / Grader graph."""
    store = SharedStore()
    uow = InMemoryUnitOfWorkFactory(store)
    ids = InMemoryIdGenerator("x")
    auth = AllowAllAuth()
    events = RecordingEventDispatcher()
    queue = RecordingRunQueue()
    actor = Actor(id="user-1")

    project = CreateProject(uow, ids, auth, events).execute(
        CreateProjectCommand(actor=actor, name="P")
    )
    grader = CreateGrader(uow, ids, auth, events).execute(
        CreateGraderCommand(actor=actor, name="G", family="objective")
    )
    gv = CreateGraderDraftVersion(uow, ids, auth, events).execute(
        CreateGraderDraftVersionCommand(
            actor=actor,
            grader_id=grader.id,
            label="v1",
            specification="ok",
        )
    )
    gv = PublishGraderVersion(uow, auth, events).execute(
        PublishGraderVersionCommand(actor=actor, grader_id=grader.id, version_id=gv.id)
    )

    case = CreateCase(uow, ids, auth, events).execute(
        CreateCaseCommand(actor=actor, project_id=project.id, name="C")
    )
    pv = CreatePromptDraftVersion(uow, ids, auth, events).execute(
        CreatePromptDraftVersionCommand(actor=actor, case_id=case.id, content="Fix it")
    )
    PublishPromptVersion(uow, auth, events).execute(
        PublishPromptVersionCommand(actor=actor, case_id=case.id, version_id=pv.id)
    )
    cv = CreateCaseDraftVersion(uow, ids, auth, events).execute(
        CreateCaseDraftVersionCommand(
            actor=actor,
            case_id=case.id,
            description="Fix the bug",
            repository_url="https://example.com/r.git",
            commit_sha="deadbeef",
            expected_checks=("pytest",),
            applicable_grader_ids=(grader.id,),
            prompt_version_id=pv.id,
        )
    )
    cv = PublishCaseVersion(uow, auth, events).execute(
        PublishCaseVersionCommand(actor=actor, case_id=case.id, version_id=cv.id)
    )

    agent = CreateAgent(uow, ids, auth, events).execute(
        CreateAgentCommand(actor=actor, name="Agent")
    )
    adapter = CreateAdapter(uow, ids, auth, events).execute(
        CreateAdapterCommand(actor=actor, agent_id=agent.id, name="Adapter")
    )
    av = CreateAgentDraftVersion(uow, ids, auth, events).execute(
        CreateAgentDraftVersionCommand(actor=actor, agent_id=agent.id, label="1.0")
    )
    av = PublishAgentVersion(uow, auth, events).execute(
        PublishAgentVersionCommand(actor=actor, agent_id=agent.id, version_id=av.id)
    )
    adv = CreateAdapterDraftVersion(uow, ids, auth, events).execute(
        CreateAdapterDraftVersionCommand(
            actor=actor, adapter_id=adapter.id, label="1.0"
        )
    )
    adv = PublishAdapterVersion(uow, auth, events).execute(
        PublishAdapterVersionCommand(
            actor=actor, adapter_id=adapter.id, version_id=adv.id
        )
    )

    return {
        "uow": uow,
        "ids": ids,
        "auth": auth,
        "events": events,
        "queue": queue,
        "idempotency": InMemoryIdempotencyStore(),
        "actor": actor,
        "project_id": project.id,
        "case_id": case.id,
        "case_version_id": cv.id,
        "prompt_version_id": pv.id,
        "agent_id": agent.id,
        "agent_version_id": av.id,
        "adapter_version_id": adv.id,
        "grader_id": grader.id,
        "grader_version_id": gv.id,
    }


def _create_run(world, *, idempotency_key: str | None = None):
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
            grader_version_refs=((world["grader_id"], world["grader_version_id"]),),
            platform_version_id="platform-1.0.0",
            idempotency_key=idempotency_key,
        )
    )


def test_create_run_queues_and_enqueues(world):
    run = _create_run(world)
    assert run.status == "queued"
    assert len(world["queue"].enqueued) == 1
    assert world["queue"].enqueued[0].value == run.id
    assert any(e.event_type == "RunCreated" for e in world["events"].events)
    assert any(e.event_type == "RunQueued" for e in world["events"].events)


def test_create_run_idempotent(world):
    first = _create_run(world, idempotency_key="run-ik")
    second = _create_run(world, idempotency_key="run-ik")
    assert first.id == second.id
    assert len(world["queue"].enqueued) == 1


def test_run_lifecycle_happy_path_with_score(world):
    run = _create_run(world)
    started = StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    assert started.status == "running"
    assert started.sandbox_id == "sb-1"

    grading = StartGrading(world["uow"], world["auth"], world["events"]).execute(
        StartGradingCommand(actor=world["actor"], run_id=run.id)
    )
    assert grading.status == "grading"

    scored = RecordScore(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        RecordScoreCommand(
            actor=world["actor"],
            run_id=run.id,
            grader_id=world["grader_id"],
            grader_version_id=world["grader_version_id"],
            passed=True,
            numeric=1.0,
        )
    )
    assert scored.produced_score_count == 1

    completed = CompleteRun(world["uow"], world["auth"], world["events"]).execute(
        CompleteRunCommand(actor=world["actor"], run_id=run.id)
    )
    assert completed.status == "completed"
    assert completed.is_partially_graded is False


def test_fail_run_is_platform_failure(world):
    run = _create_run(world)
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    failed = FailRun(world["uow"], world["auth"], world["events"]).execute(
        FailRunCommand(
            actor=world["actor"],
            run_id=run.id,
            reason="Sandbox provision failed",
        )
    )
    assert failed.status == "failed"
    assert failed.failure_reason == "Sandbox provision failed"


def test_cancel_queued_run(world):
    run = _create_run(world)
    cancelled = CancelRun(world["uow"], world["auth"], world["events"]).execute(
        CancelRunCommand(actor=world["actor"], run_id=run.id, reason="user request")
    )
    assert cancelled.status == "cancelled"


def test_invalid_transition_translated(world):
    run = _create_run(world)
    with pytest.raises(DomainTranslationError) as exc_info:
        CompleteRun(world["uow"], world["auth"], world["events"]).execute(
            CompleteRunCommand(actor=world["actor"], run_id=run.id)
        )
    assert exc_info.value.code == "INVALID_STATE_TRANSITION"


def test_record_execution_event_ordered_and_idempotent(world):
    run = _create_run(world)
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    uc = RecordExecutionEvent(world["uow"], world["auth"], world["events"])
    first = uc.execute(
        RecordExecutionEventCommand(
            actor=world["actor"],
            run_id=run.id,
            execution_event_id="evt-1",
            action={
                "kind": "message",
                "role": "assistant",
                "content_summary": "hello",
            },
        )
    )
    assert first.sequence == 0
    assert first.already_recorded is False
    second = uc.execute(
        RecordExecutionEventCommand(
            actor=world["actor"],
            run_id=run.id,
            execution_event_id="evt-2",
            action={
                "kind": "tool_call",
                "tool_name": "read",
                "arguments": {"path": "a.py"},
            },
        )
    )
    assert second.sequence == 1
    replay = uc.execute(
        RecordExecutionEventCommand(
            actor=world["actor"],
            run_id=run.id,
            execution_event_id="evt-1",
            action={
                "kind": "message",
                "role": "assistant",
                "content_summary": "hello",
            },
        )
    )
    assert replay.already_recorded is True
    assert replay.sequence == 0


def test_record_artifact_idempotent(world):
    run = _create_run(world)
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    uc = RecordArtifact(world["uow"], world["ids"], world["auth"], world["events"])
    first = uc.execute(
        RecordArtifactCommand(
            actor=world["actor"],
            run_id=run.id,
            kind="diff",
            storage_key="s3://b/a",
            content_type="text/plain",
            size_bytes=10,
            checksum="abc",
            artifact_id="art-1",
        )
    )
    assert first.already_recorded is False
    again = uc.execute(
        RecordArtifactCommand(
            actor=world["actor"],
            run_id=run.id,
            kind="diff",
            storage_key="s3://b/a",
            content_type="text/plain",
            size_bytes=10,
            checksum="abc",
            artifact_id="art-1",
        )
    )
    assert again.already_recorded is True
    assert again.id == first.id


def test_error_translation(world):
    from agent_eval_application.errors import translate_domain_error
    from agent_eval_domain.common.errors import InvariantViolation, NotFoundError

    not_found = translate_domain_error(
        NotFoundError("missing", entity="Run", entity_id="r1")
    )
    assert not_found.code == "NOT_FOUND"

    domain = translate_domain_error(InvariantViolation("bad", code="X"))
    assert domain.code == "X"
