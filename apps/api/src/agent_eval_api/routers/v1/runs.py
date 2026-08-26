"""Run endpoints — public Control Plane surface.

Supports create / get / list / cancel and nested event / artifact / score reads.
Worker lifecycle use cases (StartRun, Record*, etc.) are not exposed here.
"""

from __future__ import annotations

import os
from typing import Annotated

from agent_eval_application.artifacts.preview import (
    build_artifact_preview,
    is_previewable_artifact,
)
from agent_eval_application.commands.run import CancelRunCommand, CreateRunCommand
from agent_eval_application.commands.run_comparison import CompareRunsCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import NotFoundApplicationError
from agent_eval_application.queries.queries import (
    DiagnoseRunFailureQuery,
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunProvenanceQuery,
    GetRunQuery,
    GetRunScoresQuery,
    ListRunsByProjectQuery,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore
from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_eval_api.auth.bearer import authenticate_bearer
from agent_eval_api.auth.jwt import JwtAuthenticationError, actor_from_access_token
from agent_eval_api.dependencies import ActorDep, ContainerDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.run import (
    ArtifactPreviewResponse,
    ArtifactResponse,
    BenchmarkMatrixCellResponse,
    BenchmarkMatrixResponse,
    CancelRunRequest,
    CompareRunsRequest,
    CreateRunRequest,
    ExecutionEventResponse,
    FailingGraderReasonResponse,
    ReproducibilityResponse,
    RunComparabilityResponse,
    RunComparisonDeltaResponse,
    RunComparisonEntryResponse,
    RunComparisonResponse,
    RunDiagnosisResponse,
    RunPinsResponse,
    RunProvenanceResponse,
    RunResponse,
    RunTelemetryResponse,
    ScoreAggregateResponse,
    ScoreResponse,
)
from agent_eval_api.streaming.run_events import run_event_stream_response

router = APIRouter(prefix="/v1/runs", tags=["runs"])
_bearer = HTTPBearer(auto_error=False)


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


@router.post(
    "/compare",
    response_model=RunComparisonResponse,
    summary="Compare Runs",
)
def compare_runs(
    body: CompareRunsRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> RunComparisonResponse:
    result = services.compare_runs.execute(
        CompareRunsCommand(actor=actor, run_ids=tuple(body.run_ids))
    )
    return RunComparisonResponse(
        baseline_run_id=result.baseline_run_id,
        runs=[
            RunComparisonEntryResponse(
                run_id=entry.run_id,
                status=entry.status,
                failure_reason=entry.failure_reason,
                failure_category=entry.failure_category,
                pins=RunPinsResponse(
                    project_id=entry.pins.project_id,
                    case_version_id=entry.pins.case_version_id,
                    prompt_version_id=entry.pins.prompt_version_id,
                    agent_version_id=entry.pins.agent_version_id,
                    adapter_version_id=entry.pins.adapter_version_id,
                    platform_version_id=entry.pins.platform_version_id,
                    grader_version_ids=list(entry.pins.grader_version_ids),
                    suite_version_id=entry.pins.suite_version_id,
                ),
                repository_url=entry.repository_url,
                commit_sha=entry.commit_sha,
                adapter_key=entry.adapter_key,
                adapter_name=entry.adapter_name,
                prompt_version=entry.prompt_version,
                agent_version=entry.agent_version,
                telemetry=RunTelemetryResponse(
                    wall_clock_ms=entry.telemetry.wall_clock_ms,
                    compute_ms=entry.telemetry.compute_ms,
                    input_tokens=entry.telemetry.input_tokens,
                    output_tokens=entry.telemetry.output_tokens,
                    total_tokens=entry.telemetry.total_tokens,
                    estimated_cost=None,
                    provider_usage_available=entry.telemetry.provider_usage_available,
                ),
                score_aggregate=ScoreAggregateResponse(
                    passed=entry.score_aggregate.passed,
                    overall_score=entry.score_aggregate.overall_score,
                    objective_failed=entry.score_aggregate.objective_failed,
                    score_count=entry.score_aggregate.score_count,
                    reason=entry.score_aggregate.reason,
                ),
                duration_ms=entry.duration_ms,
                execution_mode=entry.execution_mode,
                benchmark_key=entry.benchmark_key,
                suite_version_id=entry.suite_version_id,
            )
            for entry in result.runs
        ],
        deltas=[
            RunComparisonDeltaResponse(
                run_id=delta.run_id,
                score_delta=delta.score_delta,
                pass_changed=delta.pass_changed,
                duration_delta_ms=delta.duration_delta_ms,
                pin_differences=list(delta.pin_differences),
            )
            for delta in result.deltas
        ],
        comparability=RunComparabilityResponse(
            compatible=result.comparability.compatible,
            shared_dimensions=list(result.comparability.shared_dimensions),
            agent_difference_dimensions=list(
                result.comparability.agent_difference_dimensions
            ),
            mismatches=list(result.comparability.mismatches),
            expected_agent_differences=list(
                result.comparability.expected_agent_differences
            ),
            benchmark_key=result.comparability.benchmark_key,
            notes=result.comparability.notes,
        ),
    )


@router.post(
    "/benchmark-matrix",
    response_model=BenchmarkMatrixResponse,
    summary="Benchmark evaluation matrix",
    description=(
        "Build an adapter × score matrix for runs that share the same "
        "immutable benchmark definition. Incomparable runs return comparable=false."
    ),
)
def benchmark_matrix(
    body: CompareRunsRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> BenchmarkMatrixResponse:
    result = services.build_benchmark_matrix.execute(
        CompareRunsCommand(actor=actor, run_ids=tuple(body.run_ids))
    )
    return BenchmarkMatrixResponse(
        benchmark_key=result.benchmark_key,
        comparable=result.comparable,
        notes=result.notes,
        cells=[
            BenchmarkMatrixCellResponse(
                adapter_key=cell.adapter_key,
                adapter_name=cell.adapter_name,
                execution_mode=cell.execution_mode,
                run_id=cell.run_id,
                status=cell.status,
                overall_score=cell.overall_score,
                passed=cell.passed,
                duration_ms=cell.duration_ms,
                failure_category=cell.failure_category,
            )
            for cell in result.cells
        ],
        mismatches=list(result.mismatches),
    )


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


@router.get(
    "/{run_id}/provenance",
    response_model=RunProvenanceResponse,
    summary="Get Run provenance (pins, repo SHA, adapter identity, score rollup)",
)
def get_run_provenance(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> RunProvenanceResponse:
    dto = services.get_run_provenance.execute(
        GetRunProvenanceQuery(actor=actor, run_id=run_id)
    )
    return RunProvenanceResponse(
        run_id=dto.run_id,
        status=dto.status,
        created_at=dto.created_at,
        failure_reason=dto.failure_reason,
        failure_category=dto.failure_category,
        cancellation_reason=dto.cancellation_reason,
        project_id=dto.project_id,
        case_version_id=dto.case_version_id,
        prompt_version_id=dto.prompt_version_id,
        agent_version_id=dto.agent_version_id,
        adapter_version_id=dto.adapter_version_id,
        platform_version_id=dto.platform_version_id,
        grader_version_ids=list(dto.grader_version_ids),
        suite_version_id=dto.suite_version_id,
        repository_url=dto.repository_url,
        commit_sha=dto.commit_sha,
        subdirectory=dto.subdirectory,
        agent_name=dto.agent_name,
        agent_version_label=dto.agent_version_label,
        adapter_name=dto.adapter_name,
        adapter_version_label=dto.adapter_version_label,
        adapter_key=dto.adapter_key,
        platform_name=dto.platform_name,
        platform_version_label=dto.platform_version_label,
        platform_policy_summaries=dto.platform_policy_summaries,
        grader_summaries=[dict(row) for row in dto.grader_summaries],
        score_aggregate=ScoreAggregateResponse(
            passed=dto.score_aggregate.passed,
            overall_score=dto.score_aggregate.overall_score,
            objective_failed=dto.score_aggregate.objective_failed,
            score_count=dto.score_aggregate.score_count,
            reason=dto.score_aggregate.reason,
        ),
        expected_grader_count=dto.expected_grader_count,
        produced_score_count=dto.produced_score_count,
        is_partially_graded=dto.is_partially_graded,
        telemetry=RunTelemetryResponse(
            wall_clock_ms=dto.telemetry.wall_clock_ms,
            compute_ms=dto.telemetry.compute_ms,
            input_tokens=dto.telemetry.input_tokens,
            output_tokens=dto.telemetry.output_tokens,
            total_tokens=dto.telemetry.total_tokens,
            estimated_cost=None,
            provider_usage_available=dto.telemetry.provider_usage_available,
        ),
        event_count=dto.event_count,
        artifact_count=dto.artifact_count,
        execution_mode=dto.execution_mode,
        execution_metadata=dict(dto.execution_metadata),
        benchmark_key=dto.benchmark_key,
        suite_version_id_as_benchmark=dto.suite_version_id_as_benchmark,
        reproducibility=ReproducibilityResponse(
            can_reproduce=dto.reproducibility.can_reproduce,
            missing=list(dto.reproducibility.missing),
            notes=dto.reproducibility.notes,
        ),
    )


@router.get(
    "/{run_id}/diagnosis",
    response_model=RunDiagnosisResponse,
    summary="Diagnose Run failure",
)
def diagnose_run_failure(
    run_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> RunDiagnosisResponse:
    dto = services.diagnose_run_failure.execute(
        DiagnoseRunFailureQuery(actor=actor, run_id=run_id)
    )
    return RunDiagnosisResponse(
        run_id=dto.run_id,
        status=dto.status,
        summary=dto.summary,
        category=dto.category,
        reason=dto.reason,
        evidence=list(dto.evidence),
        failing_grader_reasons=[
            FailingGraderReasonResponse(
                grader_id=row.grader_id,
                grader_version_id=row.grader_version_id,
                reason=row.reason,
            )
            for row in dto.failing_grader_reasons
        ],
        last_events=[ExecutionEventResponse.from_dto(e) for e in dto.last_events],
        relevant_artifact_ids=list(dto.relevant_artifact_ids),
    )


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
    "/{run_id}/events/stream",
    summary="Stream Run Execution Events (SSE)",
    tags=["runs", "events"],
    response_class=Response,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def stream_run_events(
    run_id: str,
    request: Request,
    services: ServicesDep,
    container: ContainerDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
    access_token: str | None = Query(
        default=None,
        description=(
            "Optional JWT for EventSource clients that cannot set Authorization"
        ),
    ),
    after_sequence: int = Query(
        default=-1,
        ge=-1,
        description="Replay durable events with sequence greater than this value",
    ),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> Response:
    """Authenticated live delivery over durable events (DB is source of truth)."""
    actor = _actor_for_sse(
        request=request,
        credentials=credentials,
        access_token=access_token,
        container=container,
    )
    cursor = after_sequence
    if last_event_id is not None and last_event_id.strip().isdigit():
        cursor = max(cursor, int(last_event_id.strip()))

    infra = getattr(container, "infrastructure", None)
    redis = getattr(infra, "redis", None) if infra is not None else None
    prefix = os.environ.get("RUN_EVENTS_CHANNEL_PREFIX", "evalforge:run-events")
    return run_event_stream_response(
        services=services,
        actor=actor,
        run_id=run_id,
        after_sequence=cursor,
        redis_client=redis,
        channel_prefix=prefix,
    )


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
    "/{run_id}/artifacts/{artifact_id}/preview",
    response_model=ArtifactPreviewResponse,
    summary="Preview Run Artifact (safe text)",
    tags=["runs", "artifacts"],
)
def preview_run_artifact(
    run_id: str,
    artifact_id: str,
    actor: ActorDep,
    services: ServicesDep,
    container: ContainerDep,
) -> ArtifactPreviewResponse:
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
    payload = b""
    if is_previewable_artifact(content_type=match.content_type, kind=match.kind):
        try:
            payload = container.infrastructure.object_storage.get(match.storage_key)
        except LookupError as exc:
            raise NotFoundApplicationError(
                f"Artifact bytes missing for {artifact_id!r}",
                entity="Artifact",
                entity_id=artifact_id,
            ) from exc
    preview = build_artifact_preview(
        artifact_id=match.id,
        content_type=match.content_type,
        size_bytes=match.size_bytes,
        kind=match.kind,
        payload=payload,
    )
    return ArtifactPreviewResponse(
        artifact_id=preview.artifact_id,
        content_type=preview.content_type,
        size_bytes=preview.size_bytes,
        preview=preview.preview,
        truncated=preview.truncated,
        previewable=preview.previewable,
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


def _actor_for_sse(
    *,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    access_token: str | None,
    container: object,
) -> Actor:
    """Resolve Actor for SSE — Bearer header or access_token query (EventSource)."""
    settings = getattr(container, "settings", None)
    if settings is None:
        raise HTTPException(status_code=500, detail="API settings unavailable")

    existing = getattr(request.state, "actor", None)
    if isinstance(existing, Actor):
        return existing

    if credentials is not None:
        return authenticate_bearer(credentials, settings)

    token = (access_token or "").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization Bearer or access_token query",
        )
    if getattr(settings, "auth_dev_accept_bearer_as_actor_id", False):
        return Actor(id=token)
    try:
        return actor_from_access_token(token, settings)
    except JwtAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
