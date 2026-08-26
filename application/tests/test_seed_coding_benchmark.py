"""Seed Coding Benchmark v1 — published multi-case suite."""

from __future__ import annotations

from agent_eval_application.benchmark_catalog import (
    CODING_BENCHMARK_V1_REPO,
    CODING_BENCHMARK_V1_SHA,
    CODING_BENCHMARK_V1_TASKS,
)
from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAdapterVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.commands.suite_execution import (
    AggregateSuiteResultsCommand,
    CreateSuiteRunsCommand,
)
from agent_eval_application.queries.queries import (
    GetSuiteQuery,
    ListSuitesByProjectQuery,
)
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
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.platform import (
    CreatePlatform,
    CreatePlatformDraftVersion,
    PublishPlatformVersion,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_application.use_cases.run import CreateRun
from agent_eval_application.use_cases.seed_coding_benchmark import SeedCodingBenchmarkV1
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    GetSuite,
    ListBenchmarkCatalog,
    PublishSuiteVersion,
)
from agent_eval_application.use_cases.suite_execution import (
    AggregateSuiteResults,
    CreateSuiteRuns,
)

pytest_plugins = ["test_run_use_cases"]


def _seed(world):
    uow, ids, auth, events = (
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
    )
    return SeedCodingBenchmarkV1(
        create_project=CreateProject(uow, ids, auth, events),
        create_grader=CreateGrader(uow, ids, auth, events),
        create_grader_draft=CreateGraderDraftVersion(uow, ids, auth, events),
        publish_grader=PublishGraderVersion(uow, auth, events),
        create_platform=CreatePlatform(uow, ids, auth, events),
        create_platform_draft=CreatePlatformDraftVersion(uow, ids, auth, events),
        publish_platform=PublishPlatformVersion(uow, auth, events),
        create_case=CreateCase(uow, ids, auth, events),
        create_prompt_draft=CreatePromptDraftVersion(uow, ids, auth, events),
        create_case_draft=CreateCaseDraftVersion(uow, ids, auth, events),
        publish_case=PublishCaseVersion(uow, auth, events),
        create_suite=CreateSuite(uow, ids, auth, events),
        create_suite_draft=CreateSuiteDraftVersion(uow, ids, auth, events),
        publish_suite=PublishSuiteVersion(uow, auth, events),
        get_suite=GetSuite(uow, auth),
    ).execute(actor=world["actor"])


def test_seed_coding_benchmark_v1_publishes_five_cases(world) -> None:
    seeded = _seed(world)
    assert len(seeded.case_version_ids) == len(CODING_BENCHMARK_V1_TASKS)
    assert seeded.suite.catalog_visible is True
    assert seeded.suite.catalog_key == "coding-benchmark-v1"
    assert seeded.suite.active_version_id == seeded.suite_version_id

    catalog = ListBenchmarkCatalog(world["uow"], world["auth"]).execute(
        ListSuitesByProjectQuery(actor=world["actor"], project_id=seeded.project_id)
    )
    assert len(catalog) == 1
    assert catalog[0].case_count == 5
    assert "bugfix" in catalog[0].categories

    suite = GetSuite(world["uow"], world["auth"]).execute(
        GetSuiteQuery(actor=world["actor"], suite_id=seeded.suite_id)
    )
    active = next(v for v in suite.versions if v.id == seeded.suite_version_id)
    assert len(active.composition) == 5


def test_seeded_benchmark_execute_scopes_execution_group(world) -> None:
    seeded = _seed(world)
    uow, ids, auth, events = (
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
    )
    agent = CreateAgent(uow, ids, auth, events).execute(
        CreateAgentCommand(actor=world["actor"], name="Seed Agent")
    )
    agent_version = CreateAgentDraftVersion(uow, ids, auth, events).execute(
        CreateAgentDraftVersionCommand(
            actor=world["actor"], agent_id=agent.id, label="1.0"
        )
    )
    agent_version = PublishAgentVersion(uow, auth, events).execute(
        PublishAgentVersionCommand(
            actor=world["actor"], agent_id=agent.id, version_id=agent_version.id
        )
    )
    adapter = CreateAdapter(uow, ids, auth, events).execute(
        CreateAdapterCommand(actor=world["actor"], agent_id=agent.id, name="gemini_cli")
    )
    adapter_version = CreateAdapterDraftVersion(uow, ids, auth, events).execute(
        CreateAdapterDraftVersionCommand(
            actor=world["actor"], adapter_id=adapter.id, label="1.0"
        )
    )
    adapter_version = PublishAdapterVersion(uow, auth, events).execute(
        PublishAdapterVersionCommand(
            actor=world["actor"],
            adapter_id=adapter.id,
            version_id=adapter_version.id,
        )
    )
    create_run = CreateRun(uow, ids, auth, events, world["queue"], world["idempotency"])
    execution = CreateSuiteRuns(uow, auth, create_run).execute(
        CreateSuiteRunsCommand(
            actor=world["actor"],
            suite_id=seeded.suite_id,
            suite_version_id=seeded.suite_version_id,
            agent_id=agent.id,
            agent_version_id=agent_version.id,
            adapter_version_id=adapter_version.id,
            platform_version_id=seeded.platform_version_id,
        )
    )
    assert execution.total_cases == 5
    assert execution.execution_group_id
    assert all(
        run.run.execution_group_id == execution.execution_group_id
        for run in execution.runs
    )
    for entry in execution.runs:
        assert entry.run.pins.case_version_id in seeded.case_version_ids

    assert CODING_BENCHMARK_V1_SHA.startswith("47329c4")
    assert "evalforge-coding-benchmark-v1" in CODING_BENCHMARK_V1_REPO

    aggregate = AggregateSuiteResults(uow, auth).execute(
        AggregateSuiteResultsCommand(
            actor=world["actor"],
            suite_id=seeded.suite_id,
            suite_version_id=seeded.suite_version_id,
            execution_group_id=execution.execution_group_id,
        )
    )
    assert aggregate.run_count == 5
    assert aggregate.execution_group_id == execution.execution_group_id
    assert aggregate.queued_or_running == 5
