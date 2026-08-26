"""HTTP GitHub repository browsing — list repos/branches and resolve HEAD SHA.

Reuses the same auth headers style as the PR publisher. Tokens are never logged
or included in error messages.
"""

from __future__ import annotations

from typing import Any

import httpx
from agent_eval_application.ports.github_repository import (
    GitHubBranchInfo,
    GitHubCommitInfo,
    GitHubRepoSummary,
)
from agent_eval_domain.common.errors import InvariantViolation


class GitHubRepositoryApiError(InvariantViolation):
    """Typed GitHub repository API failure (no secret material)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GITHUB_API_ERROR",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


def _headers(access_token: str) -> dict[str, str]:
    token = access_token.strip()
    if not token:
        raise GitHubRepositoryApiError(
            "GitHub access token is empty",
            code="EMPTY_GITHUB_TOKEN",
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EvalForge-Repository/1.0",
    }


def _short_sha(sha: str) -> str:
    cleaned = sha.strip()
    return cleaned[:7] if len(cleaned) >= 7 else cleaned


def _map_status_error(path: str, status_code: int) -> GitHubRepositoryApiError:
    if status_code in {401, 403}:
        return GitHubRepositoryApiError(
            "GitHub rejected the access token or denied repository access",
            code="GITHUB_UNAUTHORIZED",
            details={"status": status_code, "path": path},
        )
    if status_code == 404:
        return GitHubRepositoryApiError(
            "GitHub repository, branch, or commit was not found",
            code="GITHUB_NOT_FOUND",
            details={"status": status_code, "path": path},
        )
    if status_code == 429:
        return GitHubRepositoryApiError(
            "GitHub API rate limit exceeded",
            code="GITHUB_RATE_LIMITED",
            details={"status": status_code, "path": path},
        )
    return GitHubRepositoryApiError(
        f"GitHub request failed with HTTP {status_code}",
        code="GITHUB_API_ERROR",
        details={"status": status_code, "path": path},
    )


class HttpGitHubRepositoryService:
    """Real GitHub REST client for repository browsing."""

    def __init__(
        self,
        *,
        api_base: str = "https://api.github.com",
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def list_repositories(
        self, *, access_token: str, limit: int = 100
    ) -> tuple[GitHubRepoSummary, ...]:
        capped = max(1, min(limit, 100))
        payload = self._get_json(
            "/user/repos",
            access_token=access_token,
            params={
                "per_page": str(capped),
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        if not isinstance(payload, list):
            raise GitHubRepositoryApiError(
                "GitHub /user/repos returned unexpected payload",
                code="GITHUB_API_ERROR",
            )
        repos: list[GitHubRepoSummary] = []
        for item in payload[:capped]:
            if not isinstance(item, dict):
                continue
            summary = self._repo_from_payload(item)
            if summary is not None:
                repos.append(summary)
        return tuple(repos)

    def get_repository(
        self, *, owner: str, repo: str, access_token: str
    ) -> GitHubRepoSummary:
        path = f"/repos/{owner}/{repo}"
        payload = self._get_json(path, access_token=access_token)
        if not isinstance(payload, dict):
            raise GitHubRepositoryApiError(
                "GitHub repository payload was unexpected",
                code="GITHUB_API_ERROR",
                details={"path": path},
            )
        summary = self._repo_from_payload(payload)
        if summary is None:
            raise GitHubRepositoryApiError(
                "GitHub repository payload was incomplete",
                code="GITHUB_API_ERROR",
                details={"path": path},
            )
        return summary

    def list_branches(
        self, *, owner: str, repo: str, access_token: str, limit: int = 100
    ) -> tuple[GitHubBranchInfo, ...]:
        capped = max(1, min(limit, 100))
        path = f"/repos/{owner}/{repo}/branches"
        payload = self._get_json(
            path,
            access_token=access_token,
            params={"per_page": str(capped)},
        )
        if not isinstance(payload, list):
            raise GitHubRepositoryApiError(
                "GitHub branches payload was unexpected",
                code="GITHUB_API_ERROR",
                details={"path": path},
            )
        branches: list[GitHubBranchInfo] = []
        for item in payload[:capped]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            branches.append(
                GitHubBranchInfo(
                    name=name,
                    protected=bool(item.get("protected")),
                )
            )
        return tuple(branches)

    def get_branch_head(
        self, *, owner: str, repo: str, branch: str, access_token: str
    ) -> GitHubCommitInfo:
        branch_name = branch.strip()
        if not branch_name:
            raise GitHubRepositoryApiError(
                "Branch name must be non-empty",
                code="GITHUB_INVALID_BRANCH",
            )
        # Encode branch for refs that contain slashes (e.g. release/1.0).
        from urllib.parse import quote

        encoded = quote(branch_name, safe="")
        path = f"/repos/{owner}/{repo}/commits/{encoded}"
        payload = self._get_json(path, access_token=access_token)
        if not isinstance(payload, dict):
            raise GitHubRepositoryApiError(
                "GitHub commit payload was unexpected",
                code="GITHUB_API_ERROR",
                details={"path": path},
            )
        sha = str(payload.get("sha") or "").strip()
        if not sha:
            raise GitHubRepositoryApiError(
                "GitHub commit payload missing SHA",
                code="GITHUB_API_ERROR",
                details={"path": path},
            )
        commit_obj = payload.get("commit")
        commit = commit_obj if isinstance(commit_obj, dict) else {}
        message = str(commit.get("message") or "").strip() or "(no message)"
        # Prefer author date; fall back to committer.
        author_obj = commit.get("author")
        author = author_obj if isinstance(author_obj, dict) else {}
        committer_obj = commit.get("committer")
        committer = committer_obj if isinstance(committer_obj, dict) else {}
        date_raw = str(author.get("date") or committer.get("date") or "").strip()
        committed_at = date_raw or None
        html_url = str(payload.get("html_url") or "").strip() or None
        return GitHubCommitInfo(
            sha=sha,
            short_sha=_short_sha(sha),
            message=message.split("\n", 1)[0][:240],
            committed_at=committed_at,
            html_url=html_url,
        )

    def _client(self, access_token: str) -> httpx.Client:
        kwargs: dict[str, Any] = {
            "timeout": self.timeout_seconds,
            "headers": _headers(access_token),
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _get_json(
        self,
        path: str,
        *,
        access_token: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            with self._client(access_token) as client:
                response = client.get(f"{self.api_base}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise GitHubRepositoryApiError(
                "GitHub request timed out",
                code="GITHUB_TIMEOUT",
                details={"path": path},
            ) from exc
        except httpx.HTTPError as exc:
            raise GitHubRepositoryApiError(
                "GitHub request failed",
                code="GITHUB_API_ERROR",
                details={"path": path},
            ) from exc
        if response.status_code >= 400:
            raise _map_status_error(path, response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubRepositoryApiError(
                "GitHub returned non-JSON payload",
                code="GITHUB_API_ERROR",
                details={"path": path},
            ) from exc

    @staticmethod
    def _repo_from_payload(item: dict[str, Any]) -> GitHubRepoSummary | None:
        full_name = str(item.get("full_name") or "").strip()
        name = str(item.get("name") or "").strip()
        owner_obj = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        owner = str(owner_obj.get("login") or "").strip()
        if not owner and "/" in full_name:
            owner = full_name.split("/", 1)[0]
        if not name and "/" in full_name:
            name = full_name.split("/", 1)[1]
        if not owner or not name:
            return None
        default_branch = str(item.get("default_branch") or "main").strip() or "main"
        html_url = str(item.get("html_url") or "").strip()
        if not html_url:
            html_url = f"https://github.com/{owner}/{name}"
        description_raw = item.get("description")
        description = (
            str(description_raw).strip() if description_raw is not None else None
        ) or None
        return GitHubRepoSummary(
            owner=owner,
            name=name,
            full_name=full_name or f"{owner}/{name}",
            default_branch=default_branch,
            private=bool(item.get("private")),
            html_url=html_url,
            description=description,
        )
