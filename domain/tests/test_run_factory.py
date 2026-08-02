from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import (
    CaseVersionId,
    PlatformVersionId,
    ProjectId,
    RunId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
)
from agent_eval_domain.execution.run_factory import RunCreationCommand, RunFactory
from agent_eval_domain.versioning.status import VersionStatus
from helpers import (
    make_agent_and_adapter,
    make_project,
    make_published_case,
    make_published_grader,
)


def test_factory_rejects_draft_case_version() -> None:
    project = make_project()
    grader, grader_version = make_published_grader()
    case, _, prompt_version = make_published_case(
        project_id=project.id, grader_id=grader.id
    )
    # create an unpublished draft
    from agent_eval_domain.common.ids import PromptVersionId
    from agent_eval_domain.evaluation_management.case import ReferenceRepositoryState

    draft_prompt = case.prompt.create_draft_version(
        version_id=PromptVersionId("pv-draft"),
        content="draft prompt",
    )
    draft_case = case.create_draft_version(
        version_id=CaseVersionId("cv-draft"),
        description="draft case",
        reference_repository=ReferenceRepositoryState(
            repository_url="https://example.com/r.git",
            commit_sha="deadbeef",
        ),
        expected_checks=[],
        applicable_grader_ids=[grader.id],
        prompt_version_id=draft_prompt.id,
    )
    assert draft_case.status is VersionStatus.DRAFT
    _, _, agent_version, adapter_version = make_agent_and_adapter()
    with pytest.raises(InvariantViolation, match="Draft"):
        RunFactory().create(
            RunCreationCommand(
                run_id=RunId("run-x"),
                project_id=project.id,
                case_version=draft_case,
                case_project_id=project.id,
                prompt_version=draft_prompt,
                agent_version=agent_version,  # type: ignore[arg-type]
                adapter_version=adapter_version,  # type: ignore[arg-type]
                grader_versions=(grader_version,),  # type: ignore[arg-type]
                platform_version_id=PlatformVersionId("p1"),
            )
        )


def test_factory_rejects_cross_project_suite() -> None:
    project = make_project()
    other = ProjectId("other")
    grader, grader_version = make_published_grader()
    case, case_version, prompt_version = make_published_case(
        project_id=project.id, grader_id=grader.id
    )
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-1"),
        project_id=other,
        name="Other Suite",
    )
    # Compose a case from a different project — suite creation itself blocks this.
    # Simulate by building a suite version in-project then lying about suite_project_id.
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-2"),
        project_id=project.id,
        name="Suite",
    )
    sv = suite.create_draft_version(
        version_id=SuiteVersionId("sv-1"),
        composition=[
            SuiteCompositionEntry(
                case_version_id=case_version.id,
                position=0,
                case_project_id=project.id,
            )
        ],
    )
    suite.publish_version(sv.id)
    _, _, agent_version, adapter_version = make_agent_and_adapter()
    with pytest.raises(InvariantViolation, match="same Project"):
        RunFactory().create(
            RunCreationCommand(
                run_id=RunId("run-x"),
                project_id=project.id,
                case_version=case_version,  # type: ignore[arg-type]
                case_project_id=project.id,
                prompt_version=prompt_version,  # type: ignore[arg-type]
                agent_version=agent_version,  # type: ignore[arg-type]
                adapter_version=adapter_version,  # type: ignore[arg-type]
                grader_versions=(grader_version,),  # type: ignore[arg-type]
                platform_version_id=PlatformVersionId("p1"),
                suite_version=suite.active_version(),
                suite_project_id=other,
            )
        )


def test_factory_requires_declared_grader() -> None:
    project = make_project()
    grader_a, gv_a = make_published_grader(grader_id="ga")
    grader_b, gv_b = make_published_grader(grader_id="gb")
    case, case_version, prompt_version = make_published_case(
        project_id=project.id, grader_id=grader_a.id
    )
    _, _, agent_version, adapter_version = make_agent_and_adapter()
    with pytest.raises(InvariantViolation, match="not declared"):
        RunFactory().create(
            RunCreationCommand(
                run_id=RunId("run-x"),
                project_id=project.id,
                case_version=case_version,  # type: ignore[arg-type]
                case_project_id=project.id,
                prompt_version=prompt_version,  # type: ignore[arg-type]
                agent_version=agent_version,  # type: ignore[arg-type]
                adapter_version=adapter_version,  # type: ignore[arg-type]
                grader_versions=(gv_b,),  # type: ignore[arg-type]
                platform_version_id=PlatformVersionId("p1"),
            )
        )
    # sanity: declared grader works
    run = RunFactory().create(
        RunCreationCommand(
            run_id=RunId("run-ok"),
            project_id=project.id,
            case_version=case_version,  # type: ignore[arg-type]
            case_project_id=project.id,
            prompt_version=prompt_version,  # type: ignore[arg-type]
            agent_version=agent_version,  # type: ignore[arg-type]
            adapter_version=adapter_version,  # type: ignore[arg-type]
            grader_versions=(gv_a,),  # type: ignore[arg-type]
            platform_version_id=PlatformVersionId("p1"),
        )
    )
    assert run.id.value == "run-ok"
