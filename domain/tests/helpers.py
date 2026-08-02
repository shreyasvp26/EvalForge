"""Shared fixtures and builders for Domain unit tests."""

from __future__ import annotations

from agent_eval_domain.agent_integration.adapter import Adapter
from agent_eval_domain.agent_integration.agent import Agent
from agent_eval_domain.common.ids import (
    AdapterId,
    AdapterVersionId,
    AgentId,
    AgentVersionId,
    CaseId,
    CaseVersionId,
    GraderId,
    GraderVersionId,
    PlatformVersionId,
    ProjectId,
    PromptId,
    PromptVersionId,
    RunId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.case import (
    EvaluationCase,
    ReferenceRepositoryState,
)
from agent_eval_domain.evaluation_management.project import Project
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
)
from agent_eval_domain.execution.run import EvaluationRun, RunPins
from agent_eval_domain.execution.run_factory import RunCreationCommand, RunFactory
from agent_eval_domain.grading.grader import Grader, GraderFamily


def make_project(project_id: str = "proj-1") -> Project:
    return Project.create(project_id=ProjectId(project_id), name="Demo Project")


def make_published_case(
    *,
    project_id: ProjectId,
    case_id: str = "case-1",
    grader_id: GraderId | None = None,
) -> tuple[EvaluationCase, object, object]:
    case = EvaluationCase.create(
        case_id=CaseId(case_id),
        project_id=project_id,
        prompt_id=PromptId(f"prompt-{case_id}"),
        name="Fix the flaky test",
    )
    prompt_version = case.prompt.create_draft_version(
        version_id=PromptVersionId(f"pv-{case_id}"),
        content="Fix the failing unit test without changing public APIs.",
    )
    case.prompt.publish_version(prompt_version.id)
    prompt_version = case.prompt.active_version()
    assert prompt_version is not None
    graders = [grader_id] if grader_id is not None else []
    case_version = case.create_draft_version(
        version_id=CaseVersionId(f"cv-{case_id}"),
        description="Repair the race condition in the cache layer.",
        reference_repository=ReferenceRepositoryState(
            repository_url="https://example.com/repo.git",
            commit_sha="abc123def456",
        ),
        expected_checks=["pytest"],
        applicable_grader_ids=graders,
        prompt_version_id=prompt_version.id,
    )
    case.publish_version(case_version.id)
    return case, case.active_version(), prompt_version


def make_published_grader(*, grader_id: str = "grader-1") -> tuple[Grader, object]:
    grader = Grader.create(
        grader_id=GraderId(grader_id),
        name="Tests Pass",
        family=GraderFamily.OBJECTIVE,
    )
    version = grader.create_draft_version(
        version_id=GraderVersionId(f"gv-{grader_id}"),
        label="v1",
        specification="exit_code == 0 for pytest",
    )
    grader.publish_version(version.id)
    return grader, grader.active_version()


def make_agent_and_adapter() -> tuple[Agent, Adapter, object, object]:
    agent = Agent.create(agent_id=AgentId("agent-1"), name="Claude Code")
    adapter = Adapter.create(
        adapter_id=AdapterId("adapter-1"),
        agent_id=agent.id,
        name="Claude Code Adapter",
    )
    agent.connect_adapter(adapter.id)
    agent_version = agent.create_draft_version(
        version_id=AgentVersionId("av-1"),
        label="1.0.0",
    )
    agent.publish_version(agent_version.id)
    adapter_version = adapter.create_draft_version(
        version_id=AdapterVersionId("adv-1"),
        label="1.0.0",
    )
    adapter.publish_version(adapter_version.id)
    return agent, adapter, agent.active_version(), adapter.active_version()


def make_suite_with_case(
    *,
    project_id: ProjectId,
    case_version_id: object,
) -> tuple[EvaluationSuite, object]:
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-1"),
        project_id=project_id,
        name="Python Refactoring Suite",
    )
    version = suite.create_draft_version(
        version_id=SuiteVersionId("sv-1"),
        composition=[
            SuiteCompositionEntry(
                case_version_id=case_version_id,  # type: ignore[arg-type]
                position=0,
                case_project_id=project_id,
            )
        ],
    )
    suite.publish_version(version.id)
    return suite, suite.active_version()


def make_run(
    *,
    with_suite: bool = False,
) -> EvaluationRun:
    project = make_project()
    grader, grader_version = make_published_grader()
    case, case_version, prompt_version = make_published_case(
        project_id=project.id,
        grader_id=grader.id,
    )
    _, _, agent_version, adapter_version = make_agent_and_adapter()
    suite_version = None
    suite_project_id = None
    if with_suite:
        _, suite_version = make_suite_with_case(
            project_id=project.id,
            case_version_id=case_version.id,
        )
        suite_project_id = project.id

    return RunFactory().create(
        RunCreationCommand(
            run_id=RunId("run-1"),
            project_id=project.id,
            case_version=case_version,  # type: ignore[arg-type]
            case_project_id=project.id,
            prompt_version=prompt_version,  # type: ignore[arg-type]
            agent_version=agent_version,  # type: ignore[arg-type]
            adapter_version=adapter_version,  # type: ignore[arg-type]
            grader_versions=(grader_version,),  # type: ignore[arg-type]
            platform_version_id=PlatformVersionId("platform-1.0.0"),
            suite_version=suite_version,  # type: ignore[arg-type]
            suite_project_id=suite_project_id,
        )
    )


def make_direct_run_pins() -> RunPins:
    return RunPins(
        project_id=ProjectId("proj-1"),
        case_version_id=CaseVersionId("cv-1"),
        prompt_version_id=PromptVersionId("pv-1"),
        agent_version_id=AgentVersionId("av-1"),
        adapter_version_id=AdapterVersionId("adv-1"),
        platform_version_id=PlatformVersionId("platform-1"),
        grader_version_ids=(GraderVersionId("gv-1"),),
    )
