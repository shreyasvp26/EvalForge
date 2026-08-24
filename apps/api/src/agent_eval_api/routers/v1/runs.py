"""Run endpoints — public Control Plane surface.

Supports create / get / list / cancel and nested event / artifact / score reads.
Worker lifecycle use cases (StartRun, Record*, etc.) are not exposed here.
"""

from __future__ import annotations

import os
from typing import Annotated

from agent_eval_application.commands.run import CancelRunCommand, CreateRunCommand
from agent_eval_application.errors import NotFoundApplicationError
from agent_eval_application.queries.queries import (
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunQuery,
    GetRunScoresQuery,
    ListRunsByProjectQuery,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore
from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue
from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import Response

from agent_eval_api.dependencies import ActorDep, ContainerDep, ServicesDep
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
    container: ContainerDep,
    body: CancelRunRequest | None = None,
) -> RunResponse:
    reason = body.reason if body is not None else None
    dto = services.cancel_run.execute(
        CancelRunCommand(actor=actor, run_id=run_id, reason=reason)
    )
    # Fan-out cancel intent to workers (Redis) and drop pending queue entry.
    _publish_cancel_signal(container, run_id)
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
    "/{run_id}/artifacts/{artifact_id}/content",
    summary="Download Run Artifact bytes",
    tags=["runs", "artifacts"],
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_run_artifact(
    run_id: str,
    artifact_id: str,
    actor: ActorDep,
    services: ServicesDep,
    container: ContainerDep,
) -> Response:
    # AuthZ via GetRunArtifacts (project membership) then filter by id.
    items = services.get_run_artifacts.execute(
        GetRunArtifactsQuery(actor=actor, run_id=run_id)
    )
    match = next((a for a in items if a.id == artifact_id), None)
    if match is None:
        raise NotFoundApplicationError(
            f"Artifact {artifact_id!r} not found for run {run_id!r}",
            entity="Artifact",
            entity_id=artifact_id,
        )
    try:
        payload = container.infrastructure.object_storage.get(match.storage_key)
    except LookupError as exc:
        raise NotFoundApplicationError(
            f"Artifact bytes missing for {artifact_id!r}",
            entity="Artifact",
            entity_id=artifact_id,
        ) from exc
    return Response(
        content=payload,
        media_type=match.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact_id}"',
            "X-EvalForge-Checksum": match.checksum,
        },
    )


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


def _publish_cancel_signal(container: object, run_id: str) -> None:
    """Best-effort Redis cancel + dequeue. Domain cancel already succeeded."""
    infra = getattr(container, "infrastructure", None)
    if infra is None:
        return
    redis = getattr(infra, "redis", None)
    run_queue = getattr(infra, "run_queue", None)
    if redis is None:
        return
    prefix = os.environ.get("RUN_CANCEL_KEY_PREFIX", "evalforge:cancel")
    store = RedisRunCancellationStore(redis, key_prefix=prefix)
    store.request_cancel(RunId(run_id))
    if isinstance(run_queue, RedisRunQueue):
        run_queue.dequeue_pending(RunId(run_id))
