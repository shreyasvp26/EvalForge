"""Prompt endpoints — nested under Cases; Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.case import (
    CreatePromptDraftVersionCommand,
    PublishPromptVersionCommand,
)
from fastapi import APIRouter, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.case import (
    CreatePromptDraftVersionRequest,
    PromptVersionResponse,
)

router = APIRouter(prefix="/v1/cases/{case_id}/prompts", tags=["prompts"])


@router.post(
    "/versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt_draft_version(
    case_id: str,
    body: CreatePromptDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> PromptVersionResponse:
    dto = services.create_prompt_draft_version.execute(
        CreatePromptDraftVersionCommand(
            actor=actor, case_id=case_id, content=body.content
        )
    )
    return PromptVersionResponse.from_dto(dto)


@router.post(
    "/versions/{version_id}/publish",
    response_model=PromptVersionResponse,
)
def publish_prompt_version(
    case_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> PromptVersionResponse:
    dto = services.publish_prompt_version.execute(
        PublishPromptVersionCommand(actor=actor, case_id=case_id, version_id=version_id)
    )
    return PromptVersionResponse.from_dto(dto)
