"""GitHub connection + publication API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateGitHubConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, description="GitHub PAT or OAuth access token")
    display_name: str = ""
    scopes: list[str] = Field(default_factory=lambda: ["repo"])
    github_login: str | None = None


class GitHubConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    status: str
    scopes: list[str]
    github_login: str | None
    masked_token: str
    key_fingerprint: str
    created_at: str
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_port(cls, connection: object) -> GitHubConnectionResponse:
        payload = connection.to_public_dict()  # type: ignore[attr-defined]
        return cls(
            id=str(payload["id"]),
            display_name=str(payload["display_name"]),
            status=str(payload["status"]),
            scopes=[str(s) for s in list(payload.get("scopes") or [])],
            github_login=(
                str(payload["github_login"])
                if payload.get("github_login") is not None
                else None
            ),
            masked_token=str(payload["masked_token"]),
            key_fingerprint=str(payload["key_fingerprint"]),
            created_at=str(payload["created_at"]),
            metadata={
                str(k): str(v) for k, v in dict(payload.get("metadata") or {}).items()
            },
        )


class PublishRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github_connection_id: str | None = None
    base_branch: str = "main"


class PublicationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligibility: dict[str, Any] = Field(default_factory=dict)
    publication: dict[str, Any] = Field(default_factory=dict)
    run: dict[str, Any] = Field(default_factory=dict)
