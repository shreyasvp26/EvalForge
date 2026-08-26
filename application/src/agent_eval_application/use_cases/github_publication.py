"""GitHub publication use cases — CreateEvaluationPullRequest + connections."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from agent_eval_domain.common.errors import InvariantViolation, NotFoundError
from agent_eval_domain.execution.publication import (
    PublicationStatus,
    RunPublication,
    publication_branch_name,
)

from agent_eval_application.common.actor import Actor
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.github_publication import (
    CreateGitHubConnectionInput,
    GitHubConnection,
    GitHubConnectionPort,
    PublishPullRequestRequest,
    PullRequestPublisherPort,
    WorkspaceFileChange,
)
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.publication.eligibility import (
    PublicationEligibility,
    evaluate_publication_eligibility,
)
from agent_eval_application.queries.queries import GetRunQuery
from agent_eval_application.use_cases.base import with_domain_errors
from agent_eval_application.use_cases.run import GetRun


def parse_github_repository(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a github.com HTTPS or SSH URL."""
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    if cleaned.startswith("git@"):
        # git@github.com:owner/repo
        _, _, path = cleaned.partition(":")
        parts = [p for p in path.split("/") if p]
    else:
        parsed = urlparse(cleaned)
        host = (parsed.netloc or "").lower()
        if host not in {"github.com", "www.github.com"}:
            raise ApplicationValidationError(
                f"Repository URL must be on github.com (got host {host!r})",
                code="UNSUPPORTED_REPOSITORY_HOST",
            )
        parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) < 2:
        raise ApplicationValidationError(
            "Repository URL must include owner and repo",
            code="INVALID_REPOSITORY_URL",
        )
    return parts[0], parts[1]


@dataclass(frozen=True, slots=True)
class CreateGitHubConnectionCommand:
    actor: Actor
    token: str
    display_name: str = ""
    scopes: tuple[str, ...] = ()
    github_login: str | None = None


@dataclass(frozen=True, slots=True)
class ListGitHubConnectionsQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class RevokeGitHubConnectionCommand:
    actor: Actor
    connection_id: str


class CreateGitHubConnection:
    def __init__(self, store: GitHubConnectionPort) -> None:
        self._store = store

    def execute(self, command: CreateGitHubConnectionCommand) -> GitHubConnection:
        token = require_non_empty(command.token, field="token")
        return with_domain_errors(
            lambda: self._store.create(
                CreateGitHubConnectionInput(
                    user_id=command.actor.id,
                    token=token,
                    display_name=command.display_name.strip() or "GitHub",
                    scopes=command.scopes or ("repo", "public_repo", "read:user"),
                    github_login=command.github_login,
                )
            )
        )


class ListGitHubConnections:
    def __init__(self, store: GitHubConnectionPort) -> None:
        self._store = store

    def execute(self, query: ListGitHubConnectionsQuery) -> list[GitHubConnection]:
        return self._store.list_for_user(query.actor.id)


class RevokeGitHubConnection:
    def __init__(self, store: GitHubConnectionPort) -> None:
        self._store = store

    def execute(self, command: RevokeGitHubConnectionCommand) -> GitHubConnection:
        connection_id = require_non_empty(command.connection_id, field="connection_id")
        return with_domain_errors(
            lambda: self._store.revoke_for_user(
                user_id=command.actor.id, connection_id=connection_id
            )
        )


@dataclass(frozen=True, slots=True)
class CreateEvaluationPullRequestCommand:
    actor: Actor
    run_id: str
    changes: tuple[WorkspaceFileChange, ...]
    repository_url: str
    base_commit_sha: str
    case_id: str
    task_title: str
    agent_label: str = ""
    model_label: str = ""
    provider_label: str = ""
    score_summary: str = ""
    grader_summary: str = ""
    run_url: str | None = None
    github_connection_id: str | None = None
    base_branch: str = "main"


@dataclass(frozen=True, slots=True)
class CreateEvaluationPullRequestResult:
    run: RunDTO
    eligibility: PublicationEligibility
    publication: dict[str, object]


class CreateEvaluationPullRequest:
    """Publish a passed evaluation as a GitHub branch + PR.

    Failures update publication state only — never rewrite evaluation outcome.
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        events: DomainEventDispatcher,
        github_connections: GitHubConnectionPort,
        publisher: PullRequestPublisherPort,
        *,
        get_run: GetRun | None = None,
        auth: object | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._events = events
        self._github = github_connections
        self._publisher = publisher
        self._get_run = get_run
        self._auth = auth

    def execute(
        self, command: CreateEvaluationPullRequestCommand
    ) -> CreateEvaluationPullRequestResult:
        run_id = require_non_empty(command.run_id, field="run_id")
        repository_url = require_non_empty(
            command.repository_url, field="repository_url"
        )
        base_sha = require_non_empty(command.base_commit_sha, field="base_commit_sha")
        case_id = require_non_empty(command.case_id, field="case_id")

        run_dto = self._load_run(command.actor, run_id)

        # Idempotent: already-published runs return existing metadata.
        existing_pub = RunPublication.from_mapping(run_dto.publication)
        if existing_pub.is_published:
            eligibility = evaluate_publication_eligibility(
                run_status=run_dto.status,
                scores=run_dto.scores,
                publication_status=existing_pub.status,
                workspace_available=True,
                github_authorized=True,
                repository_url=repository_url,
                base_commit_sha=base_sha,
            )
            return CreateEvaluationPullRequestResult(
                run=run_dto,
                eligibility=eligibility,
                publication=existing_pub.to_public_dict(),
            )

        github_authorized = True
        access_token = ""
        try:
            _conn, access_token = self._github.resolve_token_for_user(
                user_id=command.actor.id,
                connection_id=command.github_connection_id,
            )
        except (NotFoundError, InvariantViolation, ApplicationValidationError):
            github_authorized = False

        eligibility = evaluate_publication_eligibility(
            run_status=run_dto.status,
            scores=run_dto.scores,
            publication_status=existing_pub.status,
            workspace_available=bool(command.changes),
            github_authorized=github_authorized,
            repository_url=repository_url,
            base_commit_sha=base_sha,
        )

        if not eligibility.eligible:
            current = RunPublication.from_mapping(run_dto.publication)
            if eligibility.evaluation_passed is not True:
                publication = self._persist_publication(
                    run_id,
                    current.mark_skipped(reason=eligibility.reason),
                )
            else:
                publication = self._persist_publication(
                    run_id,
                    current.mark_failed(
                        error_code="PUBLICATION_INELIGIBLE",
                        error_message=eligibility.reason,
                    ),
                )
            return CreateEvaluationPullRequestResult(
                run=self._load_run(command.actor, run_id),
                eligibility=eligibility,
                publication=publication.to_public_dict(),
            )

        owner, repo = parse_github_repository(repository_url)
        branch = publication_branch_name(case_id=case_id, run_id=run_id)
        idempotency_key = f"run:{run_id}"

        # Reuse existing PR for this branch if present.
        existing = self._publisher.find_existing_pull_request(
            owner=owner,
            repo=repo,
            branch_name=branch,
            access_token=access_token,
        )
        if existing is not None:
            publication = self._persist_publication(
                run_id,
                RunPublication(
                    status=PublicationStatus.PUBLISHED,
                    branch_name=existing.branch_name,
                    base_commit_sha=base_sha,
                    result_commit_sha=existing.result_commit_sha,
                    pull_request_url=existing.pull_request_url,
                    pull_request_number=existing.pull_request_number,
                    repository_url=repository_url,
                    idempotency_key=idempotency_key,
                ).mark_published(
                    result_commit_sha=existing.result_commit_sha,
                    pull_request_url=existing.pull_request_url,
                    pull_request_number=existing.pull_request_number,
                ),
            )
            return CreateEvaluationPullRequestResult(
                run=self._load_run(command.actor, run_id),
                eligibility=eligibility,
                publication=publication.to_public_dict(),
            )

        in_progress = RunPublication().mark_in_progress(
            branch_name=branch,
            base_commit_sha=base_sha,
            repository_url=repository_url,
            idempotency_key=idempotency_key,
        )
        self._persist_publication(run_id, in_progress)

        body = _build_pr_body(
            task_title=command.task_title,
            run_id=run_id,
            agent_label=command.agent_label,
            model_label=command.model_label,
            provider_label=command.provider_label,
            score_summary=command.score_summary,
            grader_summary=command.grader_summary,
            base_commit_sha=base_sha,
            run_url=command.run_url,
        )
        try:
            result = self._publisher.publish(
                PublishPullRequestRequest(
                    owner=owner,
                    repo=repo,
                    base_commit_sha=base_sha,
                    branch_name=branch,
                    title=f"EvalForge: {command.task_title}".strip()[:200],
                    body=body,
                    changes=command.changes,
                    base_branch=command.base_branch or "main",
                    commit_message=(f"evalforge: {command.task_title} (run {run_id})")[
                        :200
                    ],
                    idempotency_key=idempotency_key,
                ),
                access_token=access_token,
            )
        except Exception as exc:  # noqa: BLE001 — publication must not fail evaluation
            failed = in_progress.mark_failed(
                error_code="GITHUB_PUBLICATION_FAILED",
                error_message=str(exc)[:500],
            )
            publication = self._persist_publication(run_id, failed)
            return CreateEvaluationPullRequestResult(
                run=self._load_run(command.actor, run_id),
                eligibility=eligibility,
                publication=publication.to_public_dict(),
            )

        published = in_progress.mark_published(
            result_commit_sha=result.result_commit_sha,
            pull_request_url=result.pull_request_url,
            pull_request_number=result.pull_request_number,
        )
        publication = self._persist_publication(run_id, published)
        return CreateEvaluationPullRequestResult(
            run=self._load_run(command.actor, run_id),
            eligibility=eligibility,
            publication=publication.to_public_dict(),
        )

    def _load_run(self, actor: Actor, run_id: str) -> RunDTO:
        if self._get_run is not None:
            return self._get_run.execute(GetRunQuery(actor=actor, run_id=run_id))
        with self._uow_factory() as uow:
            run = uow.runs.get(run_id)
            return RunDTO.from_domain(run)

    def _persist_publication(
        self, run_id: str, publication: RunPublication
    ) -> RunPublication:
        def _write() -> RunPublication:
            with self._uow_factory() as uow:
                run = uow.runs.get(run_id)
                run.record_publication(publication)
                uow.runs.save(run)
                uow.commit()
                self._events.dispatch(run.pull_events())
                return run.publication

        return with_domain_errors(_write)


def _build_pr_body(
    *,
    task_title: str,
    run_id: str,
    agent_label: str,
    model_label: str,
    provider_label: str,
    score_summary: str,
    grader_summary: str,
    base_commit_sha: str,
    run_url: str | None,
) -> str:
    lines = [
        "## EvalForge evaluation",
        "",
        f"**Task:** {task_title or '(untitled)'}",
        f"**Run:** `{run_id}`",
    ]
    if agent_label:
        lines.append(f"**Agent:** {agent_label}")
    if model_label:
        lines.append(f"**Model:** {model_label}")
    if provider_label:
        lines.append(f"**Provider:** {provider_label}")
    if score_summary:
        lines.append(f"**Score:** {score_summary}")
    if grader_summary:
        lines.append(f"**Graders:** {grader_summary}")
    lines.append(f"**Base commit:** `{base_commit_sha}`")
    if run_url:
        lines.append(f"**EvalForge run:** {run_url}")
    lines.extend(
        [
            "",
            "Created automatically after a **passed** evaluation.",
            "Human review and merge remain required — EvalForge never merges to main.",
        ]
    )
    return "\n".join(lines)
