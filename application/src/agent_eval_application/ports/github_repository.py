"""Application port for GitHub repository browsing (read-only).

Uses the caller's existing GitHub connection token. Never returns secrets.
Task revisions still store repository URL + exact commit SHA only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GitHubRepoSummary:
    owner: str
    name: str
    full_name: str
    default_branch: str
    private: bool
    html_url: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class GitHubBranchInfo:
    name: str
    protected: bool = False


@dataclass(frozen=True, slots=True)
class GitHubCommitInfo:
    sha: str
    short_sha: str
    message: str
    committed_at: str | None = None
    html_url: str | None = None


class GitHubRepositoryPort(Protocol):
    """Read-only GitHub repository introspection for task revision pinning."""

    def list_repositories(
        self, *, access_token: str, limit: int = 100
    ) -> tuple[GitHubRepoSummary, ...]: ...

    def get_repository(
        self, *, owner: str, repo: str, access_token: str
    ) -> GitHubRepoSummary: ...

    def list_branches(
        self, *, owner: str, repo: str, access_token: str, limit: int = 100
    ) -> tuple[GitHubBranchInfo, ...]: ...

    def get_branch_head(
        self, *, owner: str, repo: str, branch: str, access_token: str
    ) -> GitHubCommitInfo: ...
