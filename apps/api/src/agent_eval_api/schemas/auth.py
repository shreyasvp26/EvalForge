"""Auth request / response schemas."""

from __future__ import annotations

from agent_eval_application.dto.user import UserDTO
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    display_name: str

    @classmethod
    def from_dto(cls, dto: UserDTO) -> UserResponse:
        return cls(id=dto.id, email=dto.email, display_name=dto.display_name)


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
