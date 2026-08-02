"""Project endpoints — invoke Application use cases only."""

from __future__ import annotations

from agent_eval_application.commands.project import (
    CreateProjectCommand,
    DeprecateProjectCommand,
    RenameProjectCommand,
    UpdateProjectSettingsCommand,
)
from agent_eval_application.queries.queries import GetProjectQuery, ListProjectsQuery
from fastapi import APIRouter, Header, status

from agent_eval_api.dependencies import ActorDep, ContainerDep, ServicesDep
from agent_eval_api.schemas.common import CollectionResponse
from agent_eval_api.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
    RenameProjectRequest,
    UpdateProjectSettingsRequest,
)

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a Project. Optional Idempotency-Key enables safe retries.",
)
def create_project(
    body: CreateProjectRequest,
    actor: ActorDep,
    services: ServicesDep,
    container: ContainerDep,
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
    # Grant Owner outside Application (membership is not a Domain concept).
    grant = getattr(container.auth, "grant", None)
    if callable(grant):
        grant(actor_id=actor.id, project_id=dto.id)
    return ProjectResponse.from_dto(dto)


@router.get(
    "",
    response_model=CollectionResponse[ProjectResponse],
    summary="List Projects",
    description="List Projects visible to the authenticated actor.",
)
def list_projects(
    actor: ActorDep,
    services: ServicesDep,
) -> CollectionResponse[ProjectResponse]:
    items = services.list_projects.execute(ListProjectsQuery(actor=actor))
    responses = [ProjectResponse.from_dto(p) for p in items]
    return CollectionResponse(items=responses, count=len(responses))


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project",
)
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
