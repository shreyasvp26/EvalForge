"""Suite fan-out execution and provenance tests."""

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
from agent_eval_application.commands.run import (
    CompleteRunCommand,
    CreateRunCommand,
    FailRunCommand,
    RecordExecutionConfigurationCommand,
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
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.provenance import GetRunProvenance
from agent_eval_application.use_cases.run import (
    CompleteRun,
    CreateRun,
    FailRun,
    RecordExecutionConfiguration,
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
            platform_version_id=world["platform_version_id"],
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
            platform_version_id=world["platform_version_id"],
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
    assert provenance.platform_version_id == world["platform_version_id"]
    assert provenance.platform_name == "Test Platform"
    assert provenance.platform_version_label == "Test Platform v1"
    assert provenance.platform_policy_summaries["sandbox"] == {
        "network_mode": "isolated"
    }
    assert provenance.execution_mode is None
    assert provenance.execution_metadata == {}

    StartRun(world["uow"], world["auth"], world["events"]).execute(
        StartRunCommand(actor=world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    RecordExecutionConfiguration(world["uow"], world["auth"], world["events"]).execute(
        RecordExecutionConfigurationCommand(
            actor=world["actor"],
            run_id=run.id,
            execution_mode="deterministic",
            metadata={
                "adapter_key": "claude_code",
                "sandbox_engine": "fake",
                "api_key": "sk-leak",
            },
        )
    )
    provenance_after = GetRunProvenance(world["uow"], world["auth"]).execute(
        GetRunProvenanceQuery(actor=world["actor"], run_id=run.id)
    )
    assert provenance_after.execution_mode == "deterministic"
    assert provenance_after.execution_metadata == {
        "adapter_key": "claude_code",
        "sandbox_engine": "fake",
    }
    assert "api_key" not in provenance_after.execution_metadata
    assert "sk-leak" not in str(provenance_after.execution_metadata)


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
            platform_version_id=world["platform_version_id"],
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
            platform_version_id=world["platform_version_id"],
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


def test_create_suite_runs_rejects_unsupported_adapter(world):
    from agent_eval_application.errors import ApplicationValidationError

    suite = CreateSuite(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateSuiteCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            name="Unsupported Adapter Bench",
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

    agent = CreateAgent(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(CreateAgentCommand(actor=world["actor"], name="Cursor Agent"))
    adapter = CreateAdapter(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateAdapterCommand(actor=world["actor"], agent_id=agent.id, name="cursor")
    )
    agent_version = CreateAgentDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateAgentDraftVersionCommand(
            actor=world["actor"], agent_id=agent.id, label="1.0"
        )
    )
    agent_version = PublishAgentVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishAgentVersionCommand(
            actor=world["actor"], agent_id=agent.id, version_id=agent_version.id
        )
    )
    adapter_version = CreateAdapterDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateAdapterDraftVersionCommand(
            actor=world["actor"], adapter_id=adapter.id, label="1.0"
        )
    )
    adapter_version = PublishAdapterVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishAdapterVersionCommand(
            actor=world["actor"],
            adapter_id=adapter.id,
            version_id=adapter_version.id,
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
    with pytest.raises(ApplicationValidationError) as exc:
        CreateSuiteRuns(world["uow"], world["auth"], create_run).execute(
            CreateSuiteRunsCommand(
                actor=world["actor"],
                suite_id=suite.id,
                suite_version_id=published.id,
                agent_id=agent.id,
                agent_version_id=agent_version.id,
                adapter_version_id=adapter_version.id,
                platform_version_id=world["platform_version_id"],
            )
        )
    assert exc.value.code == "ADAPTER_UNSUPPORTED"
