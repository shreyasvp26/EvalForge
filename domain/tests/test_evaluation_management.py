from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import (
    CaseVersionId,
    ProjectId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
)
from agent_eval_domain.versioning.status import VersionStatus
from helpers import make_project, make_published_case, make_published_grader


def test_project_requires_name() -> None:
    with pytest.raises(InvariantViolation):
        make_project()
        from agent_eval_domain.common.ids import ProjectId as Pid
        from agent_eval_domain.evaluation_management.project import Project

        Project.create(project_id=Pid("p"), name="   ")


def test_suite_rejects_cross_project_composition() -> None:
    project = make_project()
    other = ProjectId("other-project")
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-1"),
        project_id=project.id,
        name="Suite",
    )
    with pytest.raises(InvariantViolation, match="Project boundaries"):
        suite.create_draft_version(
            version_id=SuiteVersionId("sv-1"),
            composition=[
                SuiteCompositionEntry(
                    case_version_id=CaseVersionId("cv-1"),
                    position=0,
                    case_project_id=other,
                )
            ],
        )


def test_suite_versioning_forward_never_mutates_history() -> None:
    project = make_project()
    grader, _ = make_published_grader()
    case, case_version, _ = make_published_case(
        project_id=project.id, grader_id=grader.id
    )
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-1"),
        project_id=project.id,
        name="Suite",
    )
    v1 = suite.create_draft_version(
        version_id=SuiteVersionId("sv-1"),
        composition=[
            SuiteCompositionEntry(
                case_version_id=case_version.id,
                position=0,
                case_project_id=project.id,
            )
        ],
    )
    suite.publish_version(v1.id)
    assert suite.active_version() is not None
    assert suite.active_version().status is VersionStatus.ACTIVE

    # second case version for a new composition
    _, case_version_2, _ = make_published_case(
        project_id=project.id, case_id="case-2", grader_id=grader.id
    )
    v2 = suite.create_draft_version(
        version_id=SuiteVersionId("sv-2"),
        composition=[
            SuiteCompositionEntry(
                case_version_id=case_version.id,
                position=0,
                case_project_id=project.id,
            ),
            SuiteCompositionEntry(
                case_version_id=case_version_2.id,
                position=1,
                case_project_id=project.id,
            ),
        ],
    )
    suite.publish_version(v2.id)
    assert suite.get_version(v1.id).status is VersionStatus.SUPERSEDED
    assert suite.get_version(v1.id).composition[0].case_version_id == case_version.id
    assert suite.active_version().id == v2.id


def test_case_and_prompt_publish_together() -> None:
    project = make_project()
    grader, _ = make_published_grader()
    case, case_version, prompt_version = make_published_case(
        project_id=project.id, grader_id=grader.id
    )
    assert case_version.status is VersionStatus.ACTIVE
    assert prompt_version.status is VersionStatus.ACTIVE
    assert case_version.prompt_version_id == prompt_version.id
    assert case.project_id == project.id
