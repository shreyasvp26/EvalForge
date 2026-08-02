"""Authentication and authorization adapters for the API Layer."""

from agent_eval_api.auth.authorization import AllowAllAuthorization
from agent_eval_api.auth.bearer import authenticate_bearer
from agent_eval_api.auth.jwt import (
    JwtAuthenticationError,
    ParsedAccessToken,
    actor_from_access_token,
    issue_access_token,
    parse_access_token,
)
from agent_eval_api.auth.rbac import ProjectRbacAuthorization

__all__ = [
    "AllowAllAuthorization",
    "JwtAuthenticationError",
    "ParsedAccessToken",
    "ProjectRbacAuthorization",
    "actor_from_access_token",
    "authenticate_bearer",
    "issue_access_token",
    "parse_access_token",
]
