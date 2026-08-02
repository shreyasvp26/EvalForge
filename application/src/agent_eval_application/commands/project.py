"""Project commands."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    actor: Actor
    name: str
    description: str = ""
    settings: dict[str, str] = field(default_factory=dict)
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class RenameProjectCommand:
    actor: Actor
    project_id: str
    name: str


@dataclass(frozen=True, slots=True)
class UpdateProjectSettingsCommand:
    actor: Actor
    project_id: str
    settings: dict[str, str]


@dataclass(frozen=True, slots=True)
class DeprecateProjectCommand:
    actor: Actor
    project_id: str
