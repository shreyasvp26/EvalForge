"""Case endpoints — invoke Application use cases only."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    DeprecateCaseCommand,
    PublishCaseVersionCommand,
)
from agent_eval_application.queries.queries import GetCaseQuery, ListCasesByProjectQuery
from fastapi import APIRouter, Depends, Header, Query, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.pagination import ListParams
from agent_eval_api.schemas.case import (
    CaseResponse,
    CaseVersionResponse,
    CreateCaseDraftVersionRequest,
    CreateCaseRequest,
)
from agent_eval_api.schemas.common import CollectionResponse

router = APIRouter(prefix="/v1/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CreateCaseRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CaseResponse:
    dto = services.create_case.execute(
        CreateCaseCommand(
            actor=actor,
            project_id=body.project_id,
            name=body.name,
            description=body.description,
            category=body.category,
            difficulty=body.difficulty,
            language=body.language,
            tags=tuple(body.tags),
            idempotency_key=idempotency_key,
        )
    )
    return CaseResponse.from_dto(dto)


@router.get("", response_model=CollectionResponse[CaseResponse])
def list_cases(
    actor: ActorDep,
    services: ServicesDep,
    params: Annotated[ListParams, Depends()],
    project_id: str = Query(min_length=1),
) -> CollectionResponse[CaseResponse]:
    items = services.list_cases_by_project.execute(
        ListCasesByProjectQuery(actor=actor, project_id=project_id)
    )
    responses = [CaseResponse.from_dto(c) for c in items]
    return params.apply(responses)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> CaseResponse:
    dto = services.get_case.execute(GetCaseQuery(actor=actor, case_id=case_id))
    return CaseResponse.from_dto(dto)


@router.post(
    "/{case_id}/versions",
    response_model=CaseVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case_draft_version(
    case_id: str,
    body: CreateCaseDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> CaseVersionResponse:
    dto = services.create_case_draft_version.execute(
        CreateCaseDraftVersionCommand(
            actor=actor,
            case_id=case_id,
            description=body.description,
            repository_url=body.repository_url,
            commit_sha=body.commit_sha,
            expected_checks=tuple(body.expected_checks),
            applicable_grader_ids=tuple(body.applicable_grader_ids),
            prompt_version_id=body.prompt_version_id,
            subdirectory=body.subdirectory,
        )
    )
    return CaseVersionResponse.from_dto(dto)


@router.post(
    "/{case_id}/versions/{version_id}/publish",
    response_model=CaseVersionResponse,
)
def publish_case_version(
    case_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> CaseVersionResponse:
    dto = services.publish_case_version.execute(
        PublishCaseVersionCommand(actor=actor, case_id=case_id, version_id=version_id)
    )
    return CaseVersionResponse.from_dto(dto)


@router.post("/{case_id}/deprecate", response_model=CaseResponse)
def deprecate_case(
    case_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> CaseResponse:
    dto = services.deprecate_case.execute(
        DeprecateCaseCommand(actor=actor, case_id=case_id)
    )
    return CaseResponse.from_dto(dto)
