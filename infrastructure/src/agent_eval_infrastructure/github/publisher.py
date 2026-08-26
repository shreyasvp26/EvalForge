"""GitHub Pull Request publisher — Git Data API + Pulls API.

Never force-pushes. Never modifies default branch. Idempotent by branch name.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

import httpx
from agent_eval_application.ports.github_publication import (
    PublishPullRequestRequest,
    PublishPullRequestResult,
    PullRequestPublisherPort,
    WorkspaceFileChange,
)
from agent_eval_domain.common.errors import InvariantViolation


class GitHubApiError(InvariantViolation):
    def __init__(
        self, message: str, *, details: dict[str, object] | None = None
    ) -> None:
        super().__init__(
            message,
            code="GITHUB_API_ERROR",
            details=details,
        )


@dataclass
class HttpGitHubPullRequestPublisher(PullRequestPublisherPort):
    """Real GitHub API client (httpx). Token never logged."""

    api_base: str = "https://api.github.com"
    timeout_seconds: float = 30.0

    def publish(
        self,
        request: PublishPullRequestRequest,
        *,
        access_token: str,
    ) -> PublishPullRequestResult:
        existing = self.find_existing_pull_request(
            owner=request.owner,
            repo=request.repo,
            branch_name=request.branch_name,
            access_token=access_token,
        )
        if existing is not None:
            return existing

        headers = _headers(access_token)
        with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
            base = self._get_commit(
                client, request.owner, request.repo, request.base_commit_sha
            )
            base_tree_sha = str(base["tree"]["sha"])
            tree_entries = self._build_tree_entries(
                client,
                owner=request.owner,
                repo=request.repo,
                changes=request.changes,
            )
            if not tree_entries:
                raise GitHubApiError(
                    "No file changes to publish",
                    details={"branch": request.branch_name},
                )
            tree = self._post_json(
                client,
                f"/repos/{request.owner}/{request.repo}/git/trees",
                {
                    "base_tree": base_tree_sha,
                    "tree": tree_entries,
                },
            )
            commit = self._post_json(
                client,
                f"/repos/{request.owner}/{request.repo}/git/commits",
                {
                    "message": request.commit_message,
                    "tree": tree["sha"],
                    "parents": [request.base_commit_sha],
                },
            )
            result_sha = str(commit["sha"])
            # Create branch ref — fail if unrelated branch already exists.
            ref_path = f"refs/heads/{request.branch_name}"
            try:
                self._post_json(
                    client,
                    f"/repos/{request.owner}/{request.repo}/git/refs",
                    {"ref": ref_path, "sha": result_sha},
                )
            except GitHubApiError as exc:
                # If ref exists for this exact SHA, continue; else refuse overwrite.
                existing_ref = self._get_optional(
                    client,
                    f"/repos/{request.owner}/{request.repo}/git/ref/heads/"
                    f"{request.branch_name}",
                )
                if existing_ref is None:
                    raise
                existing_sha = str(existing_ref.get("object", {}).get("sha") or "")
                if existing_sha != result_sha:
                    raise GitHubApiError(
                        "Branch already exists with different commits; "
                        "refusing to overwrite",
                        details={"branch": request.branch_name},
                    ) from exc

            pr = self._post_json(
                client,
                f"/repos/{request.owner}/{request.repo}/pulls",
                {
                    "title": request.title,
                    "head": request.branch_name,
                    "base": request.base_branch,
                    "body": request.body,
                },
            )
            return PublishPullRequestResult(
                branch_name=request.branch_name,
                result_commit_sha=result_sha,
                pull_request_url=str(pr.get("html_url") or ""),
                pull_request_number=int(pr["number"]),
                created=True,
                already_existed=False,
            )

    def find_existing_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        branch_name: str,
        access_token: str,
    ) -> PublishPullRequestResult | None:
        headers = _headers(access_token)
        with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
            pulls = self._get_json(
                client,
                f"/repos/{owner}/{repo}/pulls",
                params={"state": "all", "head": f"{owner}:{branch_name}"},
            )
            if not isinstance(pulls, list) or not pulls:
                return None
            pr = pulls[0]
            head = pr.get("head") or {}
            sha = str(head.get("sha") or "")
            return PublishPullRequestResult(
                branch_name=branch_name,
                result_commit_sha=sha,
                pull_request_url=str(pr.get("html_url") or ""),
                pull_request_number=int(pr["number"]),
                created=False,
                already_existed=True,
            )

    def _get_commit(
        self, client: httpx.Client, owner: str, repo: str, sha: str
    ) -> dict[str, Any]:
        return self._get_json(client, f"/repos/{owner}/{repo}/git/commits/{sha}")

    def _build_tree_entries(
        self,
        client: httpx.Client,
        *,
        owner: str,
        repo: str,
        changes: tuple[WorkspaceFileChange, ...],
    ) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for change in changes:
            path = change.path.strip().lstrip("./")
            if not path or path.startswith(".git/"):
                continue
            if change.status == "deleted" or change.content is None:
                entries.append(
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": None,
                    }
                )
                continue
            blob = self._post_json(
                client,
                f"/repos/{owner}/{repo}/git/blobs",
                {
                    "content": base64.b64encode(change.content).decode("ascii"),
                    "encoding": "base64",
                },
            )
            entries.append(
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )
        return entries

    def _get_json(
        self,
        client: httpx.Client,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Any:
        response = client.get(f"{self.api_base}{path}", params=params)
        if response.status_code >= 400:
            raise GitHubApiError(
                f"GitHub GET {path} failed with {response.status_code}",
                details={"status": response.status_code},
            )
        return response.json()

    def _get_optional(self, client: httpx.Client, path: str) -> dict[str, Any] | None:
        response = client.get(f"{self.api_base}{path}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise GitHubApiError(
                f"GitHub GET {path} failed with {response.status_code}",
                details={"status": response.status_code},
            )
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def _post_json(
        self, client: httpx.Client, path: str, payload: dict[str, object]
    ) -> dict[str, Any]:
        response = client.post(f"{self.api_base}{path}", json=payload)
        if response.status_code >= 400:
            # Never include response body verbatim — may echo tokens.
            raise GitHubApiError(
                f"GitHub POST {path} failed with {response.status_code}",
                details={"status": response.status_code},
            )
        data = response.json()
        if not isinstance(data, dict):
            raise GitHubApiError(f"GitHub POST {path} returned unexpected payload")
        return data


def _headers(access_token: str) -> dict[str, str]:
    token = access_token.strip()
    if not token:
        raise GitHubApiError("GitHub access token is empty")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EvalForge-Publication/1.0",
    }


@dataclass
class FakeGitHubPullRequestPublisher(PullRequestPublisherPort):
    """In-memory publisher for unit/integration tests."""

    pulls: dict[str, PublishPullRequestResult] = field(default_factory=dict)
    fail_next: str | None = None
    publish_calls: list[PublishPullRequestRequest] = field(default_factory=list)

    def publish(
        self,
        request: PublishPullRequestRequest,
        *,
        access_token: str,
    ) -> PublishPullRequestResult:
        del access_token
        self.publish_calls.append(request)
        if self.fail_next:
            message = self.fail_next
            self.fail_next = None
            raise GitHubApiError(message)
        key = f"{request.owner}/{request.repo}:{request.branch_name}"
        existing = self.pulls.get(key)
        if existing is not None:
            return existing
        result = PublishPullRequestResult(
            branch_name=request.branch_name,
            result_commit_sha=f"result-{len(self.pulls) + 1:040d}"[:40],
            pull_request_url=(
                f"https://github.com/{request.owner}/{request.repo}/pull/"
                f"{len(self.pulls) + 1}"
            ),
            pull_request_number=len(self.pulls) + 1,
            created=True,
            already_existed=False,
        )
        self.pulls[key] = result
        return result

    def find_existing_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        branch_name: str,
        access_token: str,
    ) -> PublishPullRequestResult | None:
        del access_token
        return self.pulls.get(f"{owner}/{repo}:{branch_name}")
