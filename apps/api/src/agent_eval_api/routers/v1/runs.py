"""Run endpoints — public Control Plane surface.

Supports create / get / list / cancel and nested event / artifact / score reads.
Worker lifecycle use cases (StartRun, Record*, etc.) are not exposed here.
"""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.commands.run import CancelRunCommand, CreateRunCommand
from agent_eval_application.queries.queries import (
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunQuery,
    GetRunScoresQuery,
    ListRunsByProjectQuery,
)
from fastapi import APIRouter, Depends, Header, Query, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.run import (
    ArtifactResponse,
    CancelRunRequest,
    CreateRunRequest,
    ExecutionEventResponse,
    RunResponse,
    ScoreResponse,
)

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Run",
    description=(
        "Enqueue an Evaluation Run. Returns immediately with queued status. "
        "Optional Idempotency-Key enables safe retries."
    ),
)
def create_run(
    body: CreateRunRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> RunResponse:
    dto = services.create_run.execute(
        CreateRunCommand(
            actor=actor,
            project_id=body.project_id,
            case_id=body.case_id,
            case_version_id=body.case_version_id,
            prompt_version_id=body.prompt_version_id,
            agent_id=body.agent_id,
            agent_version_id=body.agent_version_id,
            adapter_version_id=body.adapter_version_id,
            grader_version_refs=tuple(
                (ref.grader_id, ref.grader_version_id)
                for ref in body.grader_version_refs
            ),
            platform_version_id=body.platform_version_id,
            suite_id=body.suite_id,
            suite_version_id=body.suite_version_id,
            idempotency_key=idempotency_key,
        )
    )
    return RunResponse.from_dto(dto)


@router.get(
    "",
    response_model=CollectionResponse[RunResponse],
    summary="List Runs by Project",
)
def list_runs(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
    project_id: str = Query(min_length=1),
) -> CollectionResponse[RunResponse]:
    items = services.list_runs_by_project.execute(
        ListRunsByProjectQuery(actor=actor, project_id=project_id)
    )
    responses = [RunResponse.from_dto(r) for r in items]
    return params.apply(responses)


@router.get("/{run_id}", response_model=RunResponse, summary="Get Run")
def get_run(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> RunResponse:
    dto = services.get_run.execute(GetRunQuery(actor=actor, run_id=run_id))
    return RunResponse.from_dto(dto)


@router.post(
    "/{run_id}/cancel",
    response_model=RunResponse,
    summary="Cancel Run",
)
def cancel_run(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
    body: CancelRunRequest | None = None,
) -> RunResponse:
    reason = body.reason if body is not None else None
    dto = services.cancel_run.execute(
        CancelRunCommand(actor=actor, run_id=run_id, reason=reason)
    )
    return RunResponse.from_dto(dto)


@router.get(
    "/{run_id}/events",
    response_model=CollectionResponse[ExecutionEventResponse],
    summary="List Run Execution Events",
    tags=["runs", "events"],
)
def list_run_events(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[ExecutionEventResponse]:
    items = services.get_run_events.execute(
        GetRunEventsQuery(actor=actor, run_id=run_id)
    )
    responses = [ExecutionEventResponse.from_dto(e) for e in items]
    return params.apply(responses)


@router.get(
    "/{run_id}/artifacts",
    response_model=CollectionResponse[ArtifactResponse],
    summary="List Run Artifacts",
    tags=["runs", "artifacts"],
)
def list_run_artifacts(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[ArtifactResponse]:
    items = services.get_run_artifacts.execute(
        GetRunArtifactsQuery(actor=actor, run_id=run_id)
    )
    responses = [ArtifactResponse.from_dto(a) for a in items]
    return params.apply(responses)


@router.get(
    "/{run_id}/scores",
    response_model=CollectionResponse[ScoreResponse],
    summary="List Run Scores",
    tags=["runs", "scores"],
)
def list_run_scores(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[ScoreResponse]:
    items = services.get_run_scores.execute(
        GetRunScoresQuery(actor=actor, run_id=run_id)
    )
    responses = [ScoreResponse.from_dto(s) for s in items]
    return params.apply(responses)
