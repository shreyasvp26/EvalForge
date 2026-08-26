"""Unit tests for publication domain value objects."""

from __future__ import annotations

from agent_eval_domain.execution.publication import (
    PublicationStatus,
    RunPublication,
    publication_branch_name,
)


def test_publication_branch_name_is_deterministic() -> None:
    a = publication_branch_name(case_id="case-1", run_id="run-1")
    b = publication_branch_name(case_id="case-1", run_id="run-1")
    assert a == b
    assert a.startswith("evalforge/task-")
    assert "run-1" in a


def test_publication_redacts_secret_like_error_messages() -> None:
    pub = RunPublication(
        status=PublicationStatus.FAILED,
        error_code="GITHUB_PUBLICATION_FAILED",
        error_message="token ghp_secrettoken123 failed",
    )
    payload = pub.to_public_dict()
    assert "ghp_" not in str(payload["error_message"]).lower()


def test_mark_failed_preserves_branch_metadata() -> None:
    pub = (
        RunPublication()
        .mark_in_progress(
            branch_name="evalforge/task-a-run-b",
            base_commit_sha="deadbeef",
            repository_url="https://github.com/acme/demo",
            idempotency_key="run:b",
        )
        .mark_failed(error_code="X", error_message="push rejected")
    )
    assert pub.status is PublicationStatus.FAILED
    assert pub.branch_name == "evalforge/task-a-run-b"
    assert pub.base_commit_sha == "deadbeef"


def test_record_publication_on_completed_run() -> None:
    from datetime import UTC, datetime

    from agent_eval_domain.common.ids import (
        AdapterVersionId,
        AgentVersionId,
        CaseVersionId,
        PlatformVersionId,
        ProjectId,
        PromptVersionId,
        RunId,
    )
    from agent_eval_domain.execution.run import EvaluationRun, RunPins
    from agent_eval_domain.execution.run_status import RunStatus

    run = EvaluationRun(
        id=RunId("run-1"),
        pins=RunPins(
            project_id=ProjectId("p1"),
            case_version_id=CaseVersionId("cv1"),
            prompt_version_id=PromptVersionId("pv1"),
            agent_version_id=AgentVersionId("av1"),
            adapter_version_id=AdapterVersionId("adv1"),
            platform_version_id=PlatformVersionId("pl1"),
            grader_version_ids=(),
        ),
        status=RunStatus.COMPLETED,
        created_at=datetime.now(UTC),
    )
    pub = RunPublication().mark_skipped(reason="evaluation did not pass")
    run.record_publication(pub)
    assert run.publication.status is PublicationStatus.SKIPPED
    assert run.status is RunStatus.COMPLETED
