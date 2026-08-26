"""GitHub connections, repository browsing, and evaluation publication endpoints."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.use_cases.github_publication import (
    CreateGitHubConnectionCommand,
    ListGitHubConnectionsQuery,
    RevokeGitHubConnectionCommand,
)
from agent_eval_application.use_cases.github_repository import (
    GetGitHubBranchHeadQuery,
    ListGitHubBranchesQuery,
    ListGitHubRepositoriesQuery,
)
from agent_eval_application.use_cases.publish_run import PublishEvaluationRunCommand
from agent_eval_domain.common.errors import NotFoundError
from fastapi import APIRouter, HTTPException, Query, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.github import (
    CreateGitHubConnectionRequest,
    GitHubBranchResponse,
    GitHubCommitResponse,
    GitHubConnectionResponse,
    GitHubRepoSummaryResponse,
    PublicationResponse,
    PublishRunRequest,
)
from agent_eval_api.schemas.run import RunResponse

router = APIRouter(tags=["github"])


@router.get(
    "/v1/github/connections",
    response_model=list[GitHubConnectionResponse],
    summary="List GitHub connections",
)
def list_github_connections(
    actor: ActorDep, services: ServicesDep
) -> list[GitHubConnectionResponse]:
    rows = services.list_github_connections.execute(
        ListGitHubConnectionsQuery(actor=actor)
    )
    return [GitHubConnectionResponse.from_port(row) for row in rows]


@router.post(
    "/v1/github/connections",
    response_model=GitHubConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect GitHub for publication",
)
def create_github_connection(
    body: CreateGitHubConnectionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> GitHubConnectionResponse:
    try:
        conn = services.create_github_connection.execute(
            CreateGitHubConnectionCommand(
                actor=actor,
                token=body.token,
                display_name=body.display_name,
                scopes=tuple(body.scopes),
                github_login=body.github_login,
            )
        )
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GitHubConnectionResponse.from_port(conn)


@router.delete(
    "/v1/github/connections/{connection_id}",
    response_model=GitHubConnectionResponse,
    summary="Revoke GitHub connection",
)
def revoke_github_connection(
    connection_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> GitHubConnectionResponse:
    try:
        conn = services.revoke_github_connection.execute(
            RevokeGitHubConnectionCommand(actor=actor, connection_id=connection_id)
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GitHubConnectionResponse.from_port(conn)


@router.get(
    "/v1/github/repositories",
    response_model=CollectionResponse[GitHubRepoSummaryResponse],
    summary="List GitHub repositories for the connected account",
    description=(
        "Uses the caller's encrypted Settings → GitHub connection. "
        "Never returns the access token. Pick a repository, then resolve an "
        "exact commit SHA before creating a Task revision."
    ),
)
def list_github_repositories(
    actor: ActorDep,
    services: ServicesDep,
    connection_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> CollectionResponse[GitHubRepoSummaryResponse]:
    rows = services.list_github_repositories.execute(
        ListGitHubRepositoriesQuery(
            actor=actor,
            connection_id=connection_id,
            limit=limit,
        )
    )
    items = [
        GitHubRepoSummaryResponse(
            owner=row.owner,
            name=row.name,
            full_name=row.full_name,
            default_branch=row.default_branch,
            private=row.private,
            html_url=row.html_url,
            description=row.description,
        )
        for row in rows
    ]
    return CollectionResponse(
        items=items,
        count=len(items),
        next_cursor=None,
        has_more=False,
    )


@router.get(
    "/v1/github/repositories/{owner}/{repo}/branches",
    response_model=CollectionResponse[GitHubBranchResponse],
    summary="List branches for a GitHub repository",
)
def list_github_branches(
    owner: str,
    repo: str,
    actor: ActorDep,
    services: ServicesDep,
    connection_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> CollectionResponse[GitHubBranchResponse]:
    rows = services.list_github_branches.execute(
        ListGitHubBranchesQuery(
            actor=actor,
            owner=owner,
            repo=repo,
            connection_id=connection_id,
            limit=limit,
        )
    )
    items = [
        GitHubBranchResponse(name=row.name, protected=row.protected) for row in rows
    ]
    return CollectionResponse(
        items=items,
        count=len(items),
        next_cursor=None,
        has_more=False,
    )


@router.get(
    "/v1/github/repositories/{owner}/{repo}/commits/{branch}",
    response_model=GitHubCommitResponse,
    summary="Resolve branch HEAD to an exact commit SHA",
    description=(
        "Returns the immutable commit SHA at the tip of the branch. "
        "Task/CaseVersion must store this SHA — never the branch name."
    ),
)
def get_github_branch_head(
    owner: str,
    repo: str,
    branch: str,
    actor: ActorDep,
    services: ServicesDep,
    connection_id: Annotated[str | None, Query()] = None,
) -> GitHubCommitResponse:
    commit = services.get_github_branch_head.execute(
        GetGitHubBranchHeadQuery(
            actor=actor,
            owner=owner,
            repo=repo,
            branch=branch,
            connection_id=connection_id,
        )
    )
    return GitHubCommitResponse(
        sha=commit.sha,
        short_sha=commit.short_sha,
        message=commit.message,
        committed_at=commit.committed_at,
        html_url=commit.html_url,
        repository_url=f"https://github.com/{owner}/{repo}",
        branch=branch,
    )


@router.post(
    "/v1/runs/{run_id}/publish",
    response_model=PublicationResponse,
    summary="Publish or retry GitHub PR for a passed evaluation",
)
def publish_run(
    run_id: str,
    body: PublishRunRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> PublicationResponse:
    """Idempotent publication retry.

    Prefer worker auto-publish (with live workspace capture). This endpoint
    reuses CreateEvaluationPullRequest: if a PR already exists for the run
    branch it returns that metadata; if evaluation failed it records skipped;
    if workspace changes are unavailable it records publication failure without
    altering evaluation status.
    """
    try:
        result = services.publish_evaluation_run.execute(
            PublishEvaluationRunCommand(
                actor=actor,
                run_id=run_id,
                changes=(),
                github_connection_id=body.github_connection_id,
                base_branch=body.base_branch,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PublicationResponse(
        eligibility=result.eligibility.to_public_dict(),
        publication=dict(result.publication),
        run=RunResponse.from_dto(result.run).model_dump(mode="json"),
    )
