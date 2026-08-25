"""Run comparison use case tests."""

from __future__ import annotations

from agent_eval_application.commands.run import (
    CompleteRunCommand,
    CreateRunCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.commands.run_comparison import CompareRunsCommand
from agent_eval_application.use_cases.run import (
    CompleteRun,
    CreateRun,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_application.use_cases.run_comparison import CompareRuns

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
            platform_version_id=world["platform_version_id"],
        )
    )


def _complete_run(world, run_id: str, *, passed: bool) -> None:
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run_id, sandbox_id="sb-1")
    )
    StartGrading(world["uow"], world["auth"], world["events"]).execute(
        StartGradingCommand(actor=world["actor"], run_id=run_id)
    )
    RecordScore(world["uow"], world["ids"], world["auth"], world["events"]).execute(
        RecordScoreCommand(
            actor=world["actor"],
            run_id=run_id,
            grader_id=world["grader_id"],
            grader_version_id=world["grader_version_id"],
            passed=passed,
            numeric=1.0 if passed else 0.0,
        )
    )
    CompleteRun(world["uow"], world["auth"], world["events"]).execute(
        CompleteRunCommand(actor=world["actor"], run_id=run_id)
    )


def test_compare_runs_returns_deltas(world):
    run_a = _create_run(world)
    _complete_run(world, run_a.id, passed=True)
    run_b = _create_run(world)
    _complete_run(world, run_b.id, passed=False)

    result = CompareRuns(world["uow"], world["auth"]).execute(
        CompareRunsCommand(
            actor=world["actor"],
            run_ids=(run_a.id, run_b.id),
        )
    )
    assert result.baseline_run_id == run_a.id
    assert len(result.runs) == 2
    assert result.runs[0].score_aggregate.passed is True
    assert result.runs[1].score_aggregate.passed is False
    assert len(result.deltas) == 1
    assert result.deltas[0].pass_changed is True
    assert result.runs[0].commit_sha == "deadbeef"
    assert result.runs[0].adapter_key == "claude_code"
