"""GitHub repository browsing use cases — pin Task revisions to exact SHAs.

Resolves the user's existing encrypted GitHub connection token. Never returns
tokens. Persisting branch names as revisions is forbidden by Case domain rules;
these use cases only surface exact SHAs for the UI to store.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_domain.common.errors import InvariantViolation, NotFoundError

from agent_eval_application.common.actor import Actor
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.github_publication import GitHubConnectionPort
from agent_eval_application.ports.github_repository import (
    GitHubBranchInfo,
    GitHubCommitInfo,
    GitHubRepositoryPort,
    GitHubRepoSummary,
)


@dataclass(frozen=True, slots=True)
class ListGitHubRepositoriesQuery:
    actor: Actor
    connection_id: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class ListGitHubBranchesQuery:
    actor: Actor
    owner: str
    repo: str
    connection_id: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class GetGitHubBranchHeadQuery:
    actor: Actor
    owner: str
    repo: str
    branch: str
    connection_id: str | None = None


def _translate_github_error(exc: BaseException) -> ApplicationValidationError:
    if isinstance(exc, NotFoundError):
        return ApplicationValidationError(
            "Connect GitHub in Settings to select a repository.",
            code="GITHUB_NOT_CONNECTED",
            details=exc.details,
            cause=exc,
        )
    if isinstance(exc, InvariantViolation):
        code = exc.code or "GITHUB_API_ERROR"
        if code == "GITHUB_CONNECTION_REVOKED":
            return ApplicationValidationError(
                "GitHub connection is revoked. Reconnect GitHub in Settings.",
                code="GITHUB_NOT_CONNECTED",
                details=exc.details,
                cause=exc,
            )
        return ApplicationValidationError(
            str(exc),
            code=code,
            details=exc.details,
            cause=exc,
        )
    return ApplicationValidationError(
        "GitHub request failed",
        code="GITHUB_API_ERROR",
        cause=exc,
    )


def _with_github_errors[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except (NotFoundError, InvariantViolation) as exc:
        raise _translate_github_error(exc) from exc


class ListGitHubRepositories:
    def __init__(
        self,
        connections: GitHubConnectionPort,
        repositories: GitHubRepositoryPort,
    ) -> None:
        self._connections = connections
        self._repositories = repositories

    def execute(
        self, query: ListGitHubRepositoriesQuery
    ) -> tuple[GitHubRepoSummary, ...]:
        def _run() -> tuple[GitHubRepoSummary, ...]:
            _conn, token = self._connections.resolve_token_for_user(
                user_id=query.actor.id,
                connection_id=query.connection_id,
            )
            return self._repositories.list_repositories(
                access_token=token,
                limit=query.limit,
            )

        return _with_github_errors(_run)


class ListGitHubBranches:
    def __init__(
        self,
        connections: GitHubConnectionPort,
        repositories: GitHubRepositoryPort,
    ) -> None:
        self._connections = connections
        self._repositories = repositories

    def execute(self, query: ListGitHubBranchesQuery) -> tuple[GitHubBranchInfo, ...]:
        owner = require_non_empty(query.owner, field="owner")
        repo = require_non_empty(query.repo, field="repo")

        def _run() -> tuple[GitHubBranchInfo, ...]:
            _conn, token = self._connections.resolve_token_for_user(
                user_id=query.actor.id,
                connection_id=query.connection_id,
            )
            return self._repositories.list_branches(
                owner=owner,
                repo=repo,
                access_token=token,
                limit=query.limit,
            )

        return _with_github_errors(_run)


class GetGitHubBranchHead:
    """Resolve a branch tip to an exact commit SHA for Task revision pinning."""

    def __init__(
        self,
        connections: GitHubConnectionPort,
        repositories: GitHubRepositoryPort,
    ) -> None:
        self._connections = connections
        self._repositories = repositories

    def execute(self, query: GetGitHubBranchHeadQuery) -> GitHubCommitInfo:
        owner = require_non_empty(query.owner, field="owner")
        repo = require_non_empty(query.repo, field="repo")
        branch = require_non_empty(query.branch, field="branch")

        def _run() -> GitHubCommitInfo:
            _conn, token = self._connections.resolve_token_for_user(
                user_id=query.actor.id,
                connection_id=query.connection_id,
            )
            return self._repositories.get_branch_head(
                owner=owner,
                repo=repo,
                branch=branch,
                access_token=token,
            )

        commit = _with_github_errors(_run)
        # Defense in depth: never let a branch name leak through as "sha".
        if commit.sha.lower() in {
            "main",
            "master",
            "latest",
            "head",
            "origin/main",
            "origin/master",
        }:
            raise ApplicationValidationError(
                "Resolved revision must be an exact commit SHA, not a branch tip",
                code="BRANCH_REVISION_FORBIDDEN",
                details={"sha": commit.sha, "branch": branch},
            )
        return commit
