"""Publication eligibility — PASS gate separate from RunStatus."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.execution.publication import PublicationStatus
from agent_eval_domain.execution.run_status import RunStatus

from agent_eval_application.scoring.aggregation import ScoreAggregate, aggregate_scores


@dataclass(frozen=True, slots=True)
class PublicationEligibility:
    """Whether a Run may create a GitHub branch/PR."""

    eligible: bool
    reason: str
    evaluation_passed: bool | None
    run_status: str
    score_count: int

    def to_public_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "evaluation_passed": self.evaluation_passed,
            "run_status": self.run_status,
            "score_count": self.score_count,
        }


def evaluate_publication_eligibility(
    *,
    run_status: str | RunStatus,
    scores: object,
    publication_status: str | PublicationStatus | None = None,
    workspace_available: bool = True,
    github_authorized: bool = True,
    repository_url: str | None = None,
    base_commit_sha: str | None = None,
) -> PublicationEligibility:
    """Gate for CreateEvaluationPullRequest.

    Evaluation FAIL → not eligible (skip publication).
    Publication already published → not eligible for a *new* publish (retry
    should short-circuit via idempotency instead).
    """
    status = (
        run_status
        if isinstance(run_status, RunStatus)
        else RunStatus(str(run_status).strip())
    )
    score_list = list(scores) if scores is not None else []
    aggregate: ScoreAggregate = aggregate_scores(score_list)
    pub = None
    if publication_status is not None:
        pub = (
            publication_status
            if isinstance(publication_status, PublicationStatus)
            else PublicationStatus(str(publication_status).strip())
        )

    if status is not RunStatus.COMPLETED:
        return PublicationEligibility(
            eligible=False,
            reason=f"run status is {status.value}, expected completed",
            evaluation_passed=aggregate.passed,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if aggregate.passed is not True:
        return PublicationEligibility(
            eligible=False,
            reason=aggregate.reason or "evaluation did not pass",
            evaluation_passed=aggregate.passed,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if pub is PublicationStatus.PUBLISHED:
        return PublicationEligibility(
            eligible=False,
            reason="already published (use idempotent retry to refresh metadata)",
            evaluation_passed=True,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if not workspace_available:
        return PublicationEligibility(
            eligible=False,
            reason="workspace / changed files are not available for publication",
            evaluation_passed=True,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if not github_authorized:
        return PublicationEligibility(
            eligible=False,
            reason="GitHub repository authorization is missing or revoked",
            evaluation_passed=True,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if not (repository_url or "").strip():
        return PublicationEligibility(
            eligible=False,
            reason="repository URL is unknown",
            evaluation_passed=True,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    if not (base_commit_sha or "").strip():
        return PublicationEligibility(
            eligible=False,
            reason="base commit SHA is unknown",
            evaluation_passed=True,
            run_status=status.value,
            score_count=aggregate.score_count,
        )
    return PublicationEligibility(
        eligible=True,
        reason="evaluation passed; ready for GitHub publication",
        evaluation_passed=True,
        run_status=status.value,
        score_count=aggregate.score_count,
    )
