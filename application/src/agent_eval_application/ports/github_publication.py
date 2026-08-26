"""Application ports for GitHub repository publication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class WorkspaceFileChange:
    """One file changed relative to the evaluation base revision."""

    path: str
    content: bytes | None
    """None means the file was deleted."""

    status: str = "modified"
    """added | modified | deleted"""


@dataclass(frozen=True, slots=True)
class PublishPullRequestRequest:
    """Intent to publish a passed evaluation as a GitHub PR."""

    owner: str
    repo: str
    base_commit_sha: str
    branch_name: str
    title: str
    body: str
    changes: tuple[WorkspaceFileChange, ...]
    base_branch: str = "main"
    """Target branch for the PR (never force-pushed)."""

    commit_message: str = "evalforge: apply passed evaluation changes"
    idempotency_key: str = ""


@dataclass(frozen=True, slots=True)
class PublishPullRequestResult:
    """Outcome of a publication attempt (no secrets)."""

    branch_name: str
    result_commit_sha: str
    pull_request_url: str
    pull_request_number: int
    created: bool
    """False when an existing branch/PR for this run was reused (idempotent)."""

    already_existed: bool = False


@dataclass(frozen=True, slots=True)
class GitHubConnection:
    """User-scoped GitHub authorization identity (non-secret)."""

    id: str
    user_id: str
    display_name: str
    status: str
    scopes: tuple[str, ...]
    github_login: str | None
    key_fingerprint: str
    created_at: str
    metadata: dict[str, str] = field(default_factory=dict)

    def masked_token_hint(self) -> str:
        tip = self.key_fingerprint[-4:] if len(self.key_fingerprint) >= 4 else "****"
        return f"••••••••{tip}"

    def to_public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "status": self.status,
            "scopes": list(self.scopes),
            "github_login": self.github_login,
            "masked_token": self.masked_token_hint(),
            "key_fingerprint": self.key_fingerprint,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CreateGitHubConnectionInput:
    user_id: str
    token: str
    display_name: str = ""
    scopes: tuple[str, ...] = ()
    github_login: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class GitHubConnectionPort(Protocol):
    """CRUD + secret resolve for GitHub publication credentials."""

    def create(self, input: CreateGitHubConnectionInput) -> GitHubConnection: ...

    def list_for_user(self, user_id: str) -> list[GitHubConnection]: ...

    def get_for_user(self, *, user_id: str, connection_id: str) -> GitHubConnection: ...

    def revoke_for_user(
        self, *, user_id: str, connection_id: str
    ) -> GitHubConnection: ...

    def resolve_token_for_user(
        self, *, user_id: str, connection_id: str | None = None
    ) -> tuple[GitHubConnection, str]:
        """Return connection + plaintext token for worker/API use only."""
        ...


class PullRequestPublisherPort(Protocol):
    """Infrastructure-owned GitHub Git Data + Pull Request operations."""

    def publish(
        self,
        request: PublishPullRequestRequest,
        *,
        access_token: str,
    ) -> PublishPullRequestResult:
        """Create branch + commit + PR, or reuse existing for the same branch."""
        ...

    def find_existing_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        branch_name: str,
        access_token: str,
    ) -> PublishPullRequestResult | None:
        """Idempotency lookup by branch name."""
        ...
