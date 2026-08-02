"""User identity DTO — Application boundary for auth use cases."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.ports.identity import IdentityRecord


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: str
    email: str
    display_name: str

    @classmethod
    def from_identity(cls, identity: IdentityRecord) -> UserDTO:
        return cls(
            id=identity.id,
            email=identity.email,
            display_name=identity.display_name,
        )
