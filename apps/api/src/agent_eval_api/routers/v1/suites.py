"""Suite endpoints — invoke Application use cases only."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.commands.suite import (
    CreateSuiteCommand,
    CreateSuiteDraftVersionCommand,
    DeprecateSuiteCommand,
    PublishSuiteVersionCommand,
    RetireSuiteVersionCommand,
    SuiteCompositionEntryInput,
)
from agent_eval_application.commands.suite_execution import (
    AggregateSuiteResultsCommand,
    CreateSuiteRunsCommand,
)
from agent_eval_application.queries.queries import (
    GetSuiteQuery,
    ListSuitesByProjectQuery,
)
from fastapi import APIRouter, Depends, Header, Query, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.suite import (
    CreateSuiteDraftVersionRequest,
    CreateSuiteRequest,
    CreateSuiteRunsRequest,
    SuiteAggregateResponse,
    SuiteExecutionResponse,
    SuiteResponse,
    SuiteVersionResponse,
)

router = APIRouter(prefix="/v1/suites", tags=["suites"])


@router.post("", response_model=SuiteResponse, status_code=status.HTTP_201_CREATED)
def create_suite(
    body: CreateSuiteRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SuiteResponse:
    dto = services.create_suite.execute(
        CreateSuiteCommand(
            actor=actor,
            project_id=body.project_id,
            name=body.name,
            description=body.description,
            idempotency_key=idempotency_key,
        )
    )
    return SuiteResponse.from_dto(dto)


@router.get("", response_model=CollectionResponse[SuiteResponse])
def list_suites(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
    project_id: str = Query(min_length=1),
) -> CollectionResponse[SuiteResponse]:
    items = services.list_suites_by_project.execute(
        ListSuitesByProjectQuery(actor=actor, project_id=project_id)
    )
    responses = [SuiteResponse.from_dto(s) for s in items]
    return params.apply(responses)


@router.get("/{suite_id}", response_model=SuiteResponse)
def get_suite(
    suite_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteResponse:
    dto = services.get_suite.execute(GetSuiteQuery(actor=actor, suite_id=suite_id))
    return SuiteResponse.from_dto(dto)


@router.post(
    "/{suite_id}/versions",
    response_model=SuiteVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_suite_draft_version(
    suite_id: str,
    body: CreateSuiteDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteVersionResponse:
    dto = services.create_suite_draft_version.execute(
        CreateSuiteDraftVersionCommand(
            actor=actor,
            suite_id=suite_id,
            composition=tuple(
                SuiteCompositionEntryInput(
                    case_version_id=e.case_version_id,
                    position=e.position,
                    case_project_id=e.case_project_id,
                )
                for e in body.composition
            ),
        )
    )
    return SuiteVersionResponse.from_dto(dto)


@router.post(
    "/{suite_id}/versions/{version_id}/publish",
    response_model=SuiteVersionResponse,
)
def publish_suite_version(
    suite_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteVersionResponse:
    dto = services.publish_suite_version.execute(
        PublishSuiteVersionCommand(
            actor=actor, suite_id=suite_id, version_id=version_id
        )
    )
    return SuiteVersionResponse.from_dto(dto)


@router.post(
    "/{suite_id}/versions/{version_id}/retire",
    response_model=SuiteVersionResponse,
)
def retire_suite_version(
    suite_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteVersionResponse:
    dto = services.retire_suite_version.execute(
        RetireSuiteVersionCommand(actor=actor, suite_id=suite_id, version_id=version_id)
    )
    return SuiteVersionResponse.from_dto(dto)


@router.post("/{suite_id}/deprecate", response_model=SuiteResponse)
def deprecate_suite(
    suite_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteResponse:
    dto = services.deprecate_suite.execute(
        DeprecateSuiteCommand(actor=actor, suite_id=suite_id)
    )
    return SuiteResponse.from_dto(dto)


@router.post(
    "/{suite_id}/versions/{version_id}/execute",
    response_model=SuiteExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute suite as a benchmark — create and enqueue one Run per case",
)
def execute_suite_version(
    suite_id: str,
    version_id: str,
    body: CreateSuiteRunsRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SuiteExecutionResponse:
    refs = None
    if body.grader_version_refs is not None:
        refs = tuple(
            (ref.grader_id, ref.grader_version_id) for ref in body.grader_version_refs
        )
    dto = services.create_suite_runs.execute(
        CreateSuiteRunsCommand(
            actor=actor,
            suite_id=suite_id,
            suite_version_id=version_id,
            agent_id=body.agent_id,
            agent_version_id=body.agent_version_id,
            adapter_version_id=body.adapter_version_id,
            platform_version_id=body.platform_version_id,
            grader_version_refs=refs,
            idempotency_key=idempotency_key,
        )
    )
    return SuiteExecutionResponse.from_dto(dto)


@router.get(
    "/{suite_id}/versions/{version_id}/results",
    response_model=SuiteAggregateResponse,
    summary="Aggregate suite results across pinned Runs",
)
def get_suite_version_results(
    suite_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteAggregateResponse:
    dto = services.aggregate_suite_results.execute(
        AggregateSuiteResultsCommand(
            actor=actor,
            suite_id=suite_id,
            suite_version_id=version_id,
        )
    )
    return SuiteAggregateResponse.from_dto(dto)
