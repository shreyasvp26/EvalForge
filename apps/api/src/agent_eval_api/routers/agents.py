"""Agent endpoints — invoke Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.agent import (
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.queries.queries import GetAgentQuery
from fastapi import APIRouter, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.agent import (
    AgentResponse,
    AgentVersionResponse,
    CreateAgentDraftVersionRequest,
    CreateAgentRequest,
)

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: CreateAgentRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AgentResponse:
    dto = services.create_agent.execute(
        CreateAgentCommand(
            actor=actor,
            name=body.name,
            description=body.description,
            idempotency_key=idempotency_key,
        )
    )
    return AgentResponse.from_dto(dto)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> AgentResponse:
    dto = services.get_agent.execute(GetAgentQuery(actor=actor, agent_id=agent_id))
    return AgentResponse.from_dto(dto)


@router.post(
    "/{agent_id}/versions",
    response_model=AgentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_draft_version(
    agent_id: str,
    body: CreateAgentDraftVersionRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> AgentVersionResponse:
    dto = services.create_agent_draft_version.execute(
        CreateAgentDraftVersionCommand(
            actor=actor,
            agent_id=agent_id,
            label=body.label,
            release_notes=body.release_notes,
        )
    )
    return AgentVersionResponse.from_dto(dto)


@router.post(
    "/{agent_id}/versions/{version_id}/publish",
    response_model=AgentVersionResponse,
)
def publish_agent_version(
    agent_id: str,
    version_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> AgentVersionResponse:
    dto = services.publish_agent_version.execute(
        PublishAgentVersionCommand(
            actor=actor, agent_id=agent_id, version_id=version_id
        )
    )
    return AgentVersionResponse.from_dto(dto)
