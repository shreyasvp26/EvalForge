"""Suite fan-out execution and provenance tests."""

from __future__ import annotations

from agent_eval_application.commands.run import (
    CompleteRunCommand,
    CreateRunCommand,
    FailRunCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.commands.suite import (
    CreateSuiteCommand,
    CreateSuiteDraftVersionCommand,
    PublishSuiteVersionCommand,
    SuiteCompositionEntryInput,
)
from agent_eval_application.commands.suite_execution import (
    AggregateSuiteResultsCommand,
    CreateSuiteRunsCommand,
)
from agent_eval_application.queries.queries import GetRunProvenanceQuery
from agent_eval_application.use_cases.provenance import GetRunProvenance
from agent_eval_application.use_cases.run import (
    CompleteRun,
    CreateRun,
    FailRun,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    PublishSuiteVersion,
)
from agent_eval_application.use_cases.suite_execution import (
    AggregateSuiteResults,
    CreateSuiteRuns,
)

pytest_plugins = ("test_run_use_cases",)


def test_create_suite_runs_fan_out(world):
    suite = CreateSuite(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateSuiteCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            name="Bench",
        )
    )
    draft = CreateSuiteDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateSuiteDraftVersionCommand(
            actor=world["actor"],
            suite_id=suite.id,
            composition=(
                SuiteCompositionEntryInput(
                    case_version_id=world["case_version_id"],
                    position=0,
                    case_project_id=world["project_id"],
                ),
            ),
        )
    )
    published = PublishSuiteVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishSuiteVersionCommand(
            actor=world["actor"], suite_id=suite.id, version_id=draft.id
        )
    )

    create_run = CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    )
    execution = CreateSuiteRuns(world["uow"], world["auth"], create_run).execute(
        CreateSuiteRunsCommand(
            actor=world["actor"],
            suite_id=suite.id,
            suite_version_id=published.id,
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            platform_version_id="platform-suite-1",
        )
    )
    assert execution.total_cases == 1
    assert len(execution.runs) == 1
    assert execution.runs[0].run.pins.suite_version_id == published.id
    assert len(world["queue"].enqueued) == 1

    aggregate = AggregateSuiteResults(world["uow"], world["auth"]).execute(
        AggregateSuiteResultsCommand(
            actor=world["actor"],
            suite_id=suite.id,
            suite_version_id=published.id,
        )
    )
    assert aggregate.run_count == 1
    assert aggregate.total_cases == 1
    assert aggregate.queued_or_running == 1


def test_run_provenance_exposes_repo_and_adapter(world):
    create_run = CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    )
    run = create_run.execute(
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
    provenance = GetRunProvenance(world["uow"], world["auth"]).execute(
        GetRunProvenanceQuery(actor=world["actor"], run_id=run.id)
    )
    assert provenance.commit_sha == "deadbeef"
    assert provenance.repository_url == "https://example.com/r.git"
    assert provenance.adapter_key == "claude_code"
    assert provenance.adapter_name == "claude_code"
    assert provenance.grader_summaries
    assert provenance.platform_version_id == "platform-1.0.0"


def _start_run(world, run_id: str) -> None:
    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run_id, sandbox_id="sb-1")
    )


def _complete_with_passed(world, run_id: str, *, passed: bool) -> None:
    _start_run(world, run_id)
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
            detail={"family": "objective"},
        )
    )
    CompleteRun(world["uow"], world["auth"], world["events"]).execute(
        CompleteRunCommand(actor=world["actor"], run_id=run_id)
    )


def test_suite_aggregate_evaluation_failed_vs_execution_failed(world):
    suite = CreateSuite(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateSuiteCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            name="Bench",
        )
    )
    draft = CreateSuiteDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateSuiteDraftVersionCommand(
            actor=world["actor"],
            suite_id=suite.id,
            composition=(
                SuiteCompositionEntryInput(
                    case_version_id=world["case_version_id"],
                    position=0,
                    case_project_id=world["project_id"],
                ),
            ),
        )
    )
    published = PublishSuiteVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishSuiteVersionCommand(
            actor=world["actor"], suite_id=suite.id, version_id=draft.id
        )
    )

    create_run = CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    )
    execution = CreateSuiteRuns(world["uow"], world["auth"], create_run).execute(
        CreateSuiteRunsCommand(
            actor=world["actor"],
            suite_id=suite.id,
            suite_version_id=published.id,
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            platform_version_id="platform-suite-1",
            idempotency_key="suite-exec-1",
        )
    )
    exec_run = execution.runs[0].run
    _start_run(world, exec_run.id)
    FailRun(world["uow"], world["auth"], world["events"]).execute(
        FailRunCommand(
            actor=world["actor"],
            run_id=exec_run.id,
            reason="adapter crashed",
            category="adapter_failure",
        )
    )

    eval_run = create_run.execute(
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
            platform_version_id="platform-suite-1",
            suite_id=suite.id,
            suite_version_id=published.id,
        )
    )
    _complete_with_passed(world, eval_run.id, passed=False)

    aggregate = AggregateSuiteResults(world["uow"], world["auth"]).execute(
        AggregateSuiteResultsCommand(
            actor=world["actor"],
            suite_id=suite.id,
            suite_version_id=published.id,
        )
    )
    assert aggregate.run_count == 2
    assert aggregate.execution_failed == 1
    assert aggregate.failed == 1
    assert aggregate.evaluation_failed == 1
    assert aggregate.objective_failed_count == 1
    assert aggregate.pass_rate == 0.0
    assert aggregate.cases[0].failure_category == "adapter_failure"
