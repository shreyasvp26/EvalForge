"""Project endpoints — invoke Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.project import (
    CreateProjectCommand,
    DeprecateProjectCommand,
    RenameProjectCommand,
    UpdateProjectSettingsCommand,
)
from agent_eval_application.queries.queries import GetProjectQuery
from fastapi import APIRouter, Header, status

from agent_eval_api.dependencies import ActorDep, ServicesDep
from agent_eval_api.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
    RenameProjectRequest,
    UpdateProjectSettingsRequest,
)

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: CreateProjectRequest,
    actor: ActorDep,
    services: ServicesDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ProjectResponse:
    dto = services.create_project.execute(
        CreateProjectCommand(
            actor=actor,
            name=body.name,
            description=body.description,
            settings=body.settings,
            idempotency_key=idempotency_key,
        )
    )
    return ProjectResponse.from_dto(dto)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> ProjectResponse:
    dto = services.get_project.execute(
        GetProjectQuery(actor=actor, project_id=project_id)
    )
    return ProjectResponse.from_dto(dto)


@router.patch("/{project_id}", response_model=ProjectResponse)
def rename_project(
    project_id: str,
    body: RenameProjectRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> ProjectResponse:
    dto = services.rename_project.execute(
        RenameProjectCommand(actor=actor, project_id=project_id, name=body.name)
    )
    return ProjectResponse.from_dto(dto)


@router.patch("/{project_id}/settings", response_model=ProjectResponse)
def update_project_settings(
    project_id: str,
    body: UpdateProjectSettingsRequest,
    actor: ActorDep,
    services: ServicesDep,
) -> ProjectResponse:
    dto = services.update_project_settings.execute(
        UpdateProjectSettingsCommand(
            actor=actor, project_id=project_id, settings=body.settings
        )
    )
    return ProjectResponse.from_dto(dto)


@router.post("/{project_id}/deprecate", response_model=ProjectResponse)
def deprecate_project(
    project_id: str,
    actor: ActorDep,
    services: ServicesDep,
) -> ProjectResponse:
    dto = services.deprecate_project.execute(
        DeprecateProjectCommand(actor=actor, project_id=project_id)
    )
    return ProjectResponse.from_dto(dto)
