"""FastAPI dependency providers — API consumes Application interfaces only."""

from __future__ import annotations

from typing import Annotated

from agent_eval_application.common.actor import Actor
from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_eval_api.auth.bearer import authenticate_bearer
from agent_eval_api.composition import ApiContainer, ApplicationServices
from agent_eval_api.config import ApiSettings

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> ApiContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        msg = "API composition root is not initialized"
        raise RuntimeError(msg)
    return container


def get_settings(
    container: Annotated[ApiContainer, Depends(get_container)],
) -> ApiSettings:
    return container.settings


def get_services(
    container: Annotated[ApiContainer, Depends(get_container)],
) -> ApplicationServices:
    return container.services


def get_actor(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(_bearer)
    ] = None,
) -> Actor:
    container = get_container(request)
    return authenticate_bearer(credentials, container.settings)


ActorDep = Annotated[Actor, Depends(get_actor)]
ServicesDep = Annotated[ApplicationServices, Depends(get_services)]
SettingsDep = Annotated[ApiSettings, Depends(get_settings)]
ContainerDep = Annotated[ApiContainer, Depends(get_container)]
