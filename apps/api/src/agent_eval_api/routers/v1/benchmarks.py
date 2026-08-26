"""Benchmark catalog endpoints — thin aliases over Suite catalog surfaces."""

from __future__ import annotations

from typing import Annotated

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
    BenchmarkCatalogEntryResponse,
    CreateSuiteRunsRequest,
    SuiteAggregateResponse,
    SuiteExecutionResponse,
    SuiteResponse,
    SuiteVersionResponse,
)

router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])


@router.get("", response_model=CollectionResponse[BenchmarkCatalogEntryResponse])
def list_benchmarks(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
    project_id: str = Query(min_length=1),
) -> CollectionResponse[BenchmarkCatalogEntryResponse]:
    """Discover catalog-visible suites (published benchmarks)."""
    items = services.list_benchmark_catalog.execute(
        ListSuitesByProjectQuery(actor=actor, project_id=project_id)
    )
    responses = [
        BenchmarkCatalogEntryResponse(
            suite_id=e.suite_id,
            project_id=e.project_id,
            catalog_key=e.catalog_key,
            name=e.name,
            description=e.description,
            status=e.status,
            active_version_id=e.active_version_id,
            active_version_number=e.active_version_number,
            case_count=e.case_count,
            categories=list(e.categories),
            difficulties=list(e.difficulties),
            created_at=e.created_at,
            catalog_visible=e.catalog_visible,
        )
        for e in items
    ]
    return params.apply(responses)


@router.get("/{suite_id}", response_model=SuiteResponse)
def get_benchmark(
    suite_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> SuiteResponse:
    dto = services.get_suite.execute(GetSuiteQuery(actor=actor, suite_id=suite_id))
    return SuiteResponse.from_dto(dto)


@router.get(
    "/{suite_id}/versions",
    response_model=CollectionResponse[SuiteVersionResponse],
)
def list_benchmark_versions(
    suite_id: str,
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
) -> CollectionResponse[SuiteVersionResponse]:
    dto = services.get_suite.execute(GetSuiteQuery(actor=actor, suite_id=suite_id))
    responses = [SuiteVersionResponse.from_dto(v) for v in dto.versions]
    return params.apply(responses)


@router.post(
    "/{suite_id}/versions/{version_id}/execute",
    response_model=SuiteExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def execute_benchmark(
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
            execution_group_id=body.execution_group_id,
            idempotency_key=idempotency_key,
        )
    )
    return SuiteExecutionResponse.from_dto(dto)


@router.get(
    "/{suite_id}/versions/{version_id}/results",
    response_model=SuiteAggregateResponse,
)
def get_benchmark_results(
    suite_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
    execution_group_id: str | None = Query(default=None),
) -> SuiteAggregateResponse:
    dto = services.aggregate_suite_results.execute(
        AggregateSuiteResultsCommand(
            actor=actor,
            suite_id=suite_id,
            suite_version_id=version_id,
            execution_group_id=execution_group_id,
        )
    )
    return SuiteAggregateResponse.from_dto(dto)
