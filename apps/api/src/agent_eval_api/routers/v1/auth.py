"""Authentication endpoints — login, logout, current user.

Login verifies credentials via Application, then the API Layer mints a JWT.
Logout is a client-side discard; the endpoint confirms the caller is authenticated.
"""

from __future__ import annotations

from agent_eval_application.commands.auth import LoginCommand
from agent_eval_application.queries.queries import GetCurrentUserQuery
from fastapi import APIRouter, Response, status

from agent_eval_api.auth.jwt import issue_access_token
from agent_eval_api.dependencies import ActorDep, ServicesDep, SettingsDep
from agent_eval_api.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Sign in",
    description="Authenticate with email and password; returns a Bearer access token.",
)
def login(
    body: LoginRequest,
    services: ServicesDep,
    settings: SettingsDep,
) -> LoginResponse:
    user = services.login.execute(
        LoginCommand(email=str(body.email), password=body.password)
    )
    expires_in = settings.jwt_access_token_ttl_seconds
    token = issue_access_token(
        user.id,
        settings,
        expires_seconds=expires_in,
        extra_claims={"email": user.email, "name": user.display_name},
    )
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.from_dto(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out",
    description=(
        "Confirm the caller is authenticated. Tokens are stateless — "
        "clients must discard the access token after logout."
    ),
    response_class=Response,
)
def logout(_actor: ActorDep) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user",
    description="Return the authenticated user's profile.",
)
def me(actor: ActorDep, services: ServicesDep) -> UserResponse:
    user = services.get_current_user.execute(GetCurrentUserQuery(actor=actor))
    return UserResponse.from_dto(user)
