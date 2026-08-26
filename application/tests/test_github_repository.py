"""Application tests for GitHub repository browsing use cases."""

from __future__ import annotations

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.github_publication import (
    CreateGitHubConnectionInput,
    GitHubConnection,
)
from agent_eval_application.ports.github_repository import (
    GitHubBranchInfo,
    GitHubCommitInfo,
    GitHubRepoSummary,
)
from agent_eval_application.use_cases.github_repository import (
    GetGitHubBranchHead,
    GetGitHubBranchHeadQuery,
    ListGitHubBranches,
    ListGitHubBranchesQuery,
    ListGitHubRepositories,
    ListGitHubRepositoriesQuery,
)
from agent_eval_domain.common.errors import InvariantViolation, NotFoundError
from agent_eval_domain.evaluation_management.case import ReferenceRepositoryState
from agent_eval_infrastructure.auth.github_connection import (
    InMemoryGitHubConnectionStore,
)
from agent_eval_infrastructure.secrets.fernet_box import _derive_fernet_key


class FakeRepos:
    def __init__(self) -> None:
        self.token_seen: str | None = None
        self.fail_with: Exception | None = None
        self.repos = (
            GitHubRepoSummary(
                owner="octocat",
                name="Hello-World",
                full_name="octocat/Hello-World",
                default_branch="main",
                private=False,
                html_url="https://github.com/octocat/Hello-World",
            ),
        )
        self.branches = (GitHubBranchInfo(name="main", protected=True),)
        self.head = GitHubCommitInfo(
            sha="abcdef0123456789abcdef0123456789abcdef01",
            short_sha="abcdef0",
            message="Initial",
            committed_at="2026-08-26T00:00:00Z",
        )

    def list_repositories(
        self, *, access_token: str, limit: int = 100
    ) -> tuple[GitHubRepoSummary, ...]:
        self.token_seen = access_token
        if self.fail_with:
            raise self.fail_with
        return self.repos[:limit]

    def get_repository(
        self, *, owner: str, repo: str, access_token: str
    ) -> GitHubRepoSummary:
        self.token_seen = access_token
        if self.fail_with:
            raise self.fail_with
        return self.repos[0]

    def list_branches(
        self, *, owner: str, repo: str, access_token: str, limit: int = 100
    ) -> tuple[GitHubBranchInfo, ...]:
        self.token_seen = access_token
        if self.fail_with:
            raise self.fail_with
        return self.branches[:limit]

    def get_branch_head(
        self, *, owner: str, repo: str, branch: str, access_token: str
    ) -> GitHubCommitInfo:
        self.token_seen = access_token
        if self.fail_with:
            raise self.fail_with
        return self.head


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> InMemoryGitHubConnectionStore:
    raw = "test-provider-credentials-key-32chars!!"
    monkeypatch.setenv("PROVIDER_CREDENTIALS_KEY", raw)
    return InMemoryGitHubConnectionStore(secret_key=_derive_fernet_key(raw))


def _connect(store: InMemoryGitHubConnectionStore) -> GitHubConnection:
    return store.create(
        CreateGitHubConnectionInput(
            user_id="alice",
            token="ghp_test_token_value",
            display_name="Work",
            scopes=("repo",),
            github_login="alice",
        )
    )


def test_list_repositories_uses_connection_token(
    store: InMemoryGitHubConnectionStore,
) -> None:
    _connect(store)
    repos_port = FakeRepos()
    result = ListGitHubRepositories(store, repos_port).execute(
        ListGitHubRepositoriesQuery(actor=Actor(id="alice"))
    )
    assert result[0].full_name == "octocat/Hello-World"
    assert repos_port.token_seen == "ghp_test_token_value"
    assert "ghp_test_token_value" not in str(result)


def test_list_repositories_not_connected(
    store: InMemoryGitHubConnectionStore,
) -> None:
    with pytest.raises(ApplicationValidationError) as excinfo:
        ListGitHubRepositories(store, FakeRepos()).execute(
            ListGitHubRepositoriesQuery(actor=Actor(id="alice"))
        )
    assert excinfo.value.code == "GITHUB_NOT_CONNECTED"


def test_list_branches_and_head(
    store: InMemoryGitHubConnectionStore,
) -> None:
    _connect(store)
    repos_port = FakeRepos()
    branches = ListGitHubBranches(store, repos_port).execute(
        ListGitHubBranchesQuery(
            actor=Actor(id="alice"),
            owner="octocat",
            repo="Hello-World",
        )
    )
    assert branches[0].name == "main"
    head = GetGitHubBranchHead(store, repos_port).execute(
        GetGitHubBranchHeadQuery(
            actor=Actor(id="alice"),
            owner="octocat",
            repo="Hello-World",
            branch="main",
        )
    )
    assert head.sha == "abcdef0123456789abcdef0123456789abcdef01"
    # Exact SHA is what CaseVersion persists — never the branch name.
    pin = ReferenceRepositoryState(
        repository_url="https://github.com/octocat/Hello-World",
        commit_sha=head.sha,
    )
    assert pin.commit_sha == head.sha
    assert pin.commit_sha != "main"


def test_branch_name_cannot_be_persisted_as_revision() -> None:
    with pytest.raises(InvariantViolation) as excinfo:
        ReferenceRepositoryState(
            repository_url="https://github.com/octocat/Hello-World",
            commit_sha="main",
        )
    assert excinfo.value.code == "BRANCH_REVISION_FORBIDDEN"


def test_unauthorized_repository_translated(
    store: InMemoryGitHubConnectionStore,
) -> None:
    _connect(store)
    repos_port = FakeRepos()
    repos_port.fail_with = InvariantViolation(
        "denied",
        code="GITHUB_UNAUTHORIZED",
        details={"status": 403},
    )
    with pytest.raises(ApplicationValidationError) as excinfo:
        ListGitHubRepositories(store, repos_port).execute(
            ListGitHubRepositoriesQuery(actor=Actor(id="alice"))
        )
    assert excinfo.value.code == "GITHUB_UNAUTHORIZED"


def test_rate_limit_translated(store: InMemoryGitHubConnectionStore) -> None:
    _connect(store)
    repos_port = FakeRepos()
    repos_port.fail_with = InvariantViolation(
        "rate limited",
        code="GITHUB_RATE_LIMITED",
        details={"status": 429},
    )
    with pytest.raises(ApplicationValidationError) as excinfo:
        ListGitHubBranches(store, repos_port).execute(
            ListGitHubBranchesQuery(
                actor=Actor(id="alice"),
                owner="octocat",
                repo="Hello-World",
            )
        )
    assert excinfo.value.code == "GITHUB_RATE_LIMITED"


def test_missing_connection_id_not_found_translated(
    store: InMemoryGitHubConnectionStore,
) -> None:
    _connect(store)
    with pytest.raises(ApplicationValidationError) as excinfo:
        ListGitHubRepositories(store, FakeRepos()).execute(
            ListGitHubRepositoriesQuery(
                actor=Actor(id="alice"),
                connection_id="missing-id",
            )
        )
    assert excinfo.value.code == "GITHUB_NOT_CONNECTED"
    # Underlying was NotFoundError
    assert isinstance(excinfo.value.__cause__, NotFoundError)
