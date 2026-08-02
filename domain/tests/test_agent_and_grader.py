from __future__ import annotations

from agent_eval_domain.grading.grader import GraderFamily
from agent_eval_domain.versioning.status import VersionStatus
from helpers import make_agent_and_adapter, make_published_grader


def test_agent_adapter_connection_and_versioning() -> None:
    agent, adapter, agent_version, adapter_version = make_agent_and_adapter()
    assert agent.adapter_id == adapter.id
    assert adapter.agent_id == agent.id
    assert agent_version.status is VersionStatus.ACTIVE
    assert adapter_version.status is VersionStatus.ACTIVE
    assert agent.can_be_targeted_by_run()


def test_grader_families_share_model() -> None:
    objective, ov = make_published_grader(grader_id="obj")
    from agent_eval_domain.common.ids import GraderId, GraderVersionId
    from agent_eval_domain.grading.grader import Grader

    rubric = Grader.create(
        grader_id=GraderId("rubric"),
        name="Code Quality",
        family=GraderFamily.RUBRIC,
    )
    rv = rubric.create_draft_version(
        version_id=GraderVersionId("gv-rubric"),
        label="v1",
        specification="Score clarity 1-5",
    )
    rubric.publish_version(rv.id)
    assert objective.family is GraderFamily.OBJECTIVE
    assert rubric.family is GraderFamily.RUBRIC
    assert ov.is_pinnable()
    assert rubric.active_version() is not None
