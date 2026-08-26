"""Unit tests for HttpGitHubRepositoryService (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
from agent_eval_infrastructure.github.repository_service import (
    GitHubRepositoryApiError,
    HttpGitHubRepositoryService,
)


def _service(handler: httpx.MockTransport) -> HttpGitHubRepositoryService:
    return HttpGitHubRepositoryService(timeout_seconds=2.0, transport=handler)


def test_list_repositories() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/user/repos"
        assert request.headers.get("authorization") == "Bearer ghp_secret"
        return httpx.Response(
            200,
            json=[
                {
                    "full_name": "octocat/Hello-World",
                    "name": "Hello-World",
                    "owner": {"login": "octocat"},
                    "default_branch": "main",
                    "private": False,
                    "html_url": "https://github.com/octocat/Hello-World",
                    "description": "demo",
                }
            ],
        )

    repos = _service(httpx.MockTransport(handler)).list_repositories(
        access_token="ghp_secret"
    )
    assert len(repos) == 1
    assert repos[0].full_name == "octocat/Hello-World"
    assert repos[0].default_branch == "main"
    assert "ghp_secret" not in str(repos)


def test_list_branches() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World/branches"
        return httpx.Response(
            200,
            json=[
                {"name": "main", "protected": True},
                {"name": "develop", "protected": False},
            ],
        )

    branches = _service(httpx.MockTransport(handler)).list_branches(
        owner="octocat",
        repo="Hello-World",
        access_token="token",
    )
    assert [b.name for b in branches] == ["main", "develop"]


def test_get_branch_head_exact_sha() -> None:
    sha = "abcdef0123456789abcdef0123456789abcdef01"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World/commits/main"
        return httpx.Response(
            200,
            json={
                "sha": sha,
                "html_url": f"https://github.com/octocat/Hello-World/commit/{sha}",
                "commit": {
                    "message": "Ship it\n\nDetails",
                    "author": {"date": "2026-08-26T12:00:00Z"},
                },
            },
        )

    commit = _service(httpx.MockTransport(handler)).get_branch_head(
        owner="octocat",
        repo="Hello-World",
        branch="main",
        access_token="token",
    )
    assert commit.sha == sha
    assert commit.short_sha == "abcdef0"
    assert commit.message == "Ship it"
    assert commit.sha.lower() != "main"


def test_unauthorized_maps_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    with pytest.raises(GitHubRepositoryApiError) as excinfo:
        _service(httpx.MockTransport(handler)).list_repositories(access_token="bad")
    assert excinfo.value.code == "GITHUB_UNAUTHORIZED"
    assert "bad" not in str(excinfo.value)


def test_not_found_maps_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    with pytest.raises(GitHubRepositoryApiError) as excinfo:
        _service(httpx.MockTransport(handler)).get_branch_head(
            owner="octocat",
            repo="missing",
            branch="main",
            access_token="token",
        )
    assert excinfo.value.code == "GITHUB_NOT_FOUND"


def test_rate_limit_maps_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "API rate limit exceeded"})

    with pytest.raises(GitHubRepositoryApiError) as excinfo:
        _service(httpx.MockTransport(handler)).list_repositories(access_token="token")
    assert excinfo.value.code == "GITHUB_RATE_LIMITED"


def test_timeout_maps_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(GitHubRepositoryApiError) as excinfo:
        _service(httpx.MockTransport(handler)).list_repositories(access_token="token")
    assert excinfo.value.code == "GITHUB_TIMEOUT"
