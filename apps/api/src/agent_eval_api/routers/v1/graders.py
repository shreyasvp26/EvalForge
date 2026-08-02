"""Grader endpoints — invoke Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.queries.queries import GetGraderQuery, ListGradersQuery
from fastapi import APIRouter, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.grader import (
    CreateGraderDraftVersionRequest,
    CreateGraderRequest,
    GraderResponse,
    GraderVersionResponse,
)

router = APIRouter(prefix="/v1/graders", tags=["graders"])


@router.post(
    "",
    response_model=GraderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Grader",
)
def create_grader(
    body: CreateGraderRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> GraderResponse:
    dto = services.create_grader.execute(
        CreateGraderCommand(
            actor=actor,
            name=body.name,
            family=body.family,
            description=body.description,
            idempotency_key=idempotency_key,
        )
    )
    return GraderResponse.from_dto(dto)


@router.get(
    "",
    response_model=CollectionResponse[GraderResponse],
    summary="List Graders",
)
def list_graders(
    actor: ActorDep,
    services: ServicesDep,
) -> CollectionResponse[GraderResponse]:
    items = services.list_graders.execute(ListGradersQuery(actor=actor))
    responses = [GraderResponse.from_dto(g) for g in items]
    return CollectionResponse(items=responses, count=len(responses))


@router.get("/{grader_id}", response_model=GraderResponse, summary="Get Grader")
def get_grader(
    grader_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> GraderResponse:
    dto = services.get_grader.execute(GetGraderQuery(actor=actor, grader_id=grader_id))
    return GraderResponse.from_dto(dto)


@router.post(
    "/{grader_id}/versions",
    response_model=GraderVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_grader_draft_version(
    grader_id: str,
    body: CreateGraderDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> GraderVersionResponse:
    dto = services.create_grader_draft_version.execute(
        CreateGraderDraftVersionCommand(
            actor=actor,
            grader_id=grader_id,
            label=body.label,
            specification=body.specification,
        )
    )
    return GraderVersionResponse.from_dto(dto)


@router.post(
    "/{grader_id}/versions/{version_id}/publish",
    response_model=GraderVersionResponse,
)
def publish_grader_version(
    grader_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> GraderVersionResponse:
    dto = services.publish_grader_version.execute(
        PublishGraderVersionCommand(
            actor=actor, grader_id=grader_id, version_id=version_id
        )
    )
    return GraderVersionResponse.from_dto(dto)
