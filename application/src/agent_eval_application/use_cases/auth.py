"""Authentication use cases — credential verification and session profile."""

from __future__ import annotations

from agent_eval_application.commands.auth import LoginCommand
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.user import UserDTO
from agent_eval_application.errors import AuthenticationError
from agent_eval_application.ports.identity import IdentityPort
from agent_eval_application.queries.queries import GetCurrentUserQuery


class Login:
    """Verify email/password credentials and return the authenticated user."""

    def __init__(self, identity: IdentityPort) -> None:
        self._identity = identity

    def execute(self, command: LoginCommand) -> UserDTO:
        email = require_non_empty(command.email, field="email").strip().lower()
        password = require_non_empty(command.password, field="password")
        identity = self._identity.authenticate(email=email, password=password)
        if identity is None:
            raise AuthenticationError("Invalid email or password")
        return UserDTO.from_identity(identity)


class GetCurrentUser:
    """Resolve the authenticated actor to a user profile."""

    def __init__(self, identity: IdentityPort) -> None:
        self._identity = identity

    def execute(self, query: GetCurrentUserQuery) -> UserDTO:
        identity = self._identity.get_by_id(query.actor.id)
        if identity is None:
            raise AuthenticationError("Session is no longer valid")
        return UserDTO.from_identity(identity)
