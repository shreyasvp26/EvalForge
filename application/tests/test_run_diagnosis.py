"""Run failure diagnosis use case tests."""

from __future__ import annotations

from agent_eval_application.commands.run import (
    CompleteRunCommand,
    CreateRunCommand,
    FailRunCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.queries.queries import DiagnoseRunFailureQuery
from agent_eval_application.use_cases.run import (
    CompleteRun,
    CreateRun,
    FailRun,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_application.use_cases.run_diagnosis import DiagnoseRunFailure

pytest_plugins = ("test_run_use_cases",)


def _create_run(world):
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
        )
    )


def test_diagnose_evaluation_failure(world):
    run = _create_run(world)
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    StartGrading(world["uow"], world["auth"], world["events"]).execute(
        StartGradingCommand(actor=world["actor"], run_id=run.id)
    )
    RecordScore(world["uow"], world["ids"], world["auth"], world["events"]).execute(
        RecordScoreCommand(
            actor=world["actor"],
            run_id=run.id,
            grader_id=world["grader_id"],
            grader_version_id=world["grader_version_id"],
            passed=False,
            numeric=0.0,
            detail={"family": "objective", "reason": "tests failed"},
        )
    )
    CompleteRun(world["uow"], world["auth"], world["events"]).execute(
        CompleteRunCommand(actor=world["actor"], run_id=run.id)
    )

    diagnosis = DiagnoseRunFailure(world["uow"], world["auth"]).execute(
        DiagnoseRunFailureQuery(actor=world["actor"], run_id=run.id)
    )
    assert diagnosis.category == "evaluation_failure"
    assert diagnosis.status == "completed"
    assert diagnosis.failing_grader_reasons
    assert diagnosis.failing_grader_reasons[0].reason == "tests failed"


def test_diagnose_execution_failure(world):
    run = _create_run(world)
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    FailRun(world["uow"], world["auth"], world["events"]).execute(
        FailRunCommand(
            actor=world["actor"],
            run_id=run.id,
            reason="sandbox died",
            category="sandbox_failure",
        )
    )

    diagnosis = DiagnoseRunFailure(world["uow"], world["auth"]).execute(
        DiagnoseRunFailureQuery(actor=world["actor"], run_id=run.id)
    )
    assert diagnosis.category == "sandbox_failure"
    assert diagnosis.status == "failed"
    assert "sandbox died" in diagnosis.evidence
