"""Authentication endpoints — login, logout, current user, OAuth."""

from __future__ import annotations

from agent_eval_application.commands.auth import LoginCommand
from agent_eval_application.errors import AuthenticationError
from agent_eval_application.queries.queries import GetCurrentUserQuery
from fastapi import APIRouter, Query, Response, status
from fastapi.responses import RedirectResponse

from agent_eval_api.auth.jwt import issue_access_token
from agent_eval_api.dependencies import ActorDep, ContainerDep, ServicesDep, SettingsDep
from agent_eval_api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    OAuthExchangeRequest,
    OAuthProvidersResponse,
    UserResponse,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get(
    "/providers",
    response_model=OAuthProvidersResponse,
    summary="Available OAuth providers",
)
def oauth_providers(settings: SettingsDep) -> OAuthProvidersResponse:
    return OAuthProvidersResponse(
        google=settings.google_oauth_configured(),
        github=settings.github_oauth_configured(),
    )


@router.get(
    "/google/authorize",
    summary="Begin Google OAuth",
    response_class=RedirectResponse,
)
def google_authorize(
    container: ContainerDep,
    next: str | None = Query(default=None, max_length=512),
) -> RedirectResponse:
    url = container.oauth.begin_authorization(provider="google", next_path=next)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    response_class=RedirectResponse,
)
async def google_callback(
    container: ContainerDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    redirect_url = await _complete_oauth_callback(
        container,
        provider="google",
        code=code,
        state=state,
        error=error,
        error_description=error_description,
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/github/authorize",
    summary="Begin GitHub OAuth",
    response_class=RedirectResponse,
)
def github_authorize(
    container: ContainerDep,
    next: str | None = Query(default=None, max_length=512),
) -> RedirectResponse:
    url = container.oauth.begin_authorization(provider="github", next_path=next)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback",
    response_class=RedirectResponse,
)
async def github_callback(
    container: ContainerDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    redirect_url = await _complete_oauth_callback(
        container,
        provider="github",
        code=code,
        state=state,
        error=error,
        error_description=error_description,
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/oauth/exchange",
    response_model=LoginResponse,
    summary="Exchange OAuth session code for access token",
)
def oauth_exchange(
    body: OAuthExchangeRequest,
    container: ContainerDep,
    settings: SettingsDep,
) -> LoginResponse:
    try:
        payload = container.oauth.exchange_session(body.code)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    identity = container.identity.get_by_id(payload.user_id)
    if identity is None:
        raise AuthenticationError("Session is no longer valid")

    expires_in = settings.jwt_access_token_ttl_seconds
    token = issue_access_token(
        identity.id,
        settings,
        expires_seconds=expires_in,
        extra_claims={"email": identity.email, "name": identity.display_name},
    )
    user = container.services.get_current_user.execute(
        GetCurrentUserQuery(actor=_actor_from_user_id(identity.id))
    )
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.from_dto(user),
    )


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


async def _complete_oauth_callback(
    container: ContainerDep,
    *,
    provider: str,
    code: str | None,
    state: str | None,
    error: str | None,
    error_description: str | None,
) -> str:
    settings = container.settings
    web_base = settings.web_app_url.rstrip("/")
    try:
        return await container.oauth.complete_callback(
            provider=provider,
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )
    except AuthenticationError as exc:
        from urllib.parse import urlencode

        params = urlencode({"error": str(exc)})
        return f"{web_base}/login?{params}"


def _actor_from_user_id(user_id: str):
    from agent_eval_application.common.actor import Actor

    return Actor(id=user_id)
