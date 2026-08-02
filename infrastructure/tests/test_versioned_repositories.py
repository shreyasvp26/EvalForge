"""Suite / Case / Agent / Adapter / Grader repository tests."""

from __future__ import annotations

from dataclasses import replace

import pytest
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.ids import (
    AdapterId,
    AgentId,
    CaseId,
    CaseVersionId,
    GraderId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
    SuiteVersion,
)
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import VersionStatus

from .conftest import NOW, seed_agent_adapter, seed_case, seed_grader, seed_project


def test_case_save_get_version_and_list(repos) -> None:
    project = seed_project(repos)
    grader, _ = seed_grader(repos)
    case, case_version, prompt_version = seed_case(
        repos, project_id=project.id, grader_id=grader.id
    )

    loaded = repos["cases"].get(case.id)
    assert loaded.name == "bugfix"
    assert loaded.prompt.versions[0].content == "Fix the bug"
    assert loaded.versions[0].applicable_grader_ids == (grader.id,)

    by_version = repos["cases"].get_version(case_version.id)
    assert by_version.id == case_version.id
    assert by_version.prompt_version_id == prompt_version.id

    listed = repos["cases"].list_by_project(project.id)
    assert [c.id for c in listed] == [case.id]


def test_case_version_status_update(repos) -> None:
    project = seed_project(repos)
    grader, _ = seed_grader(repos)
    case, case_version, _ = seed_case(repos, project_id=project.id, grader_id=grader.id)

    updated = replace(case_version, status=VersionStatus.SUPERSEDED)
    case._versions = [updated]  # noqa: SLF001
    repos["cases"].save(case)
    repos["session"].flush()

    loaded = repos["cases"].get_version(CaseVersionId("case-v1"))
    assert loaded.status is VersionStatus.SUPERSEDED


def test_suite_save_get_composition_and_list(repos) -> None:
    project = seed_project(repos)
    grader, _ = seed_grader(repos)
    _, case_version, _ = seed_case(repos, project_id=project.id, grader_id=grader.id)

    suite = EvaluationSuite(
        id=SuiteId("suite-1"),
        project_id=project.id,
        name="smoke",
        description="s",
        created_at=NOW,
    )
    suite_version = SuiteVersion(
        id=SuiteVersionId("suite-v1"),
        suite_id=suite.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        composition=(
            SuiteCompositionEntry(
                case_version_id=case_version.id,
                position=0,
                case_project_id=project.id,
            ),
        ),
        predecessor_version_id=None,
        created_at=NOW,
    )
    suite._versions = [suite_version]  # noqa: SLF001
    repos["suites"].save(suite)
    repos["session"].flush()

    loaded = repos["suites"].get(suite.id)
    assert loaded.versions[0].composition[0].case_version_id == case_version.id

    by_version = repos["suites"].get_version(SuiteVersionId("suite-v1"))
    assert by_version.case_version_ids() == (case_version.id,)

    listed = repos["suites"].list_by_project(project.id)
    assert [s.id for s in listed] == [suite.id]


def test_agent_adapter_grader_roundtrip(repos) -> None:
    agent, adapter, agent_version, adapter_version = seed_agent_adapter(repos)
    grader, grader_version = seed_grader(repos)

    loaded_agent = repos["agents"].get(agent.id)
    assert loaded_agent.adapter_id == adapter.id
    assert loaded_agent.versions[0].id == agent_version.id

    loaded_adapter = repos["adapters"].get(adapter.id)
    assert loaded_adapter.versions[0].id == adapter_version.id
    assert repos["adapters"].get_by_agent(agent.id).id == adapter.id

    loaded_grader = repos["graders"].get(grader.id)
    assert loaded_grader.versions[0].id == grader_version.id
    assert loaded_grader.family.value == "objective"


def test_missing_entities(repos) -> None:
    with pytest.raises(NotFoundError):
        repos["cases"].get(CaseId("missing"))
    with pytest.raises(NotFoundError):
        repos["suites"].get(SuiteId("missing"))
    with pytest.raises(NotFoundError):
        repos["agents"].get(AgentId("missing"))
    with pytest.raises(NotFoundError):
        repos["adapters"].get(AdapterId("missing"))
    with pytest.raises(NotFoundError):
        repos["graders"].get(GraderId("missing"))
