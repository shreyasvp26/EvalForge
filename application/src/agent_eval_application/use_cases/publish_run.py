"""Publish a completed Run using case/repo context from pins."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.github_publication import (
    GitHubConnectionPort,
    PullRequestPublisherPort,
    WorkspaceFileChange,
)
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetRunQuery
from agent_eval_application.scoring.aggregation import aggregate_scores
from agent_eval_application.use_cases.github_publication import (
    CreateEvaluationPullRequest,
    CreateEvaluationPullRequestCommand,
    CreateEvaluationPullRequestResult,
)
from agent_eval_application.use_cases.run import GetRun


@dataclass(frozen=True, slots=True)
class PublishEvaluationRunCommand:
    actor: Actor
    run_id: str
    changes: tuple[WorkspaceFileChange, ...] = ()
    github_connection_id: str | None = None
    base_branch: str = "main"
    run_url: str | None = None


class PublishEvaluationRun:
    """Resolve Task/repo context from Run pins, then publish if eligible."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        events: DomainEventDispatcher,
        github_connections: GitHubConnectionPort,
        publisher: PullRequestPublisherPort,
        *,
        get_run: GetRun | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._inner = CreateEvaluationPullRequest(
            uow_factory,
            events,
            github_connections,
            publisher,
            get_run=get_run,
        )
        self._get_run = get_run or GetRun(uow_factory, auth=_AllowAllAuth())

    def execute(
        self, command: PublishEvaluationRunCommand
    ) -> CreateEvaluationPullRequestResult:
        run_id = require_non_empty(command.run_id, field="run_id")
        run = self._get_run.execute(GetRunQuery(actor=command.actor, run_id=run_id))
        context = self._resolve_context(run)
        aggregate = aggregate_scores(run.scores)
        score_summary = (
            f"passed={aggregate.passed} overall={aggregate.overall_score}"
            if aggregate.score_count
            else "no scores"
        )
        grader_summary = ", ".join(
            f"{s.grader_id}:{s.value.passed}" for s in run.scores
        )
        meta = dict(run.execution_metadata or {})
        return self._inner.execute(
            CreateEvaluationPullRequestCommand(
                actor=command.actor,
                run_id=run_id,
                changes=command.changes,
                repository_url=context["repository_url"],
                base_commit_sha=context["base_commit_sha"],
                case_id=context["case_id"],
                task_title=context["task_title"],
                agent_label=meta.get("adapter_name") or meta.get("adapter_key") or "",
                model_label=meta.get("actual_model")
                or meta.get("requested_model")
                or "",
                provider_label=meta.get("provider_key") or "",
                score_summary=score_summary,
                grader_summary=grader_summary,
                run_url=command.run_url,
                github_connection_id=command.github_connection_id
                or (run.runtime_request or {}).get("github_connection_id"),
                base_branch=command.base_branch,
            )
        )

    def _resolve_context(self, run: RunDTO) -> dict[str, str]:
        from agent_eval_domain.common.ids import CaseVersionId

        with self._uow_factory() as uow:
            case_version = uow.cases.get_version(
                CaseVersionId(run.pins.case_version_id)
            )
            case = uow.cases.get(case_version.case_id)
            ref = case_version.reference_repository
            return {
                "case_id": case.id.value,
                "task_title": case.name,
                "repository_url": ref.repository_url,
                "base_commit_sha": ref.commit_sha,
            }


class _AllowAllAuth:
    def ensure_can_access_project(self, actor: Actor, project_id: object) -> None:
        del actor, project_id
