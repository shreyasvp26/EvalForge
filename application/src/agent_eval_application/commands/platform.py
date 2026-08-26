"""Platform catalog commands."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreatePlatformCommand:
    actor: Actor
    name: str
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CreatePlatformDraftVersionCommand:
    actor: Actor
    platform_id: str
    label: str
    sandbox_policy: dict[str, str] = field(default_factory=dict)
    execution_policy: dict[str, str] = field(default_factory=dict)
    timeout_policy: dict[str, str] = field(default_factory=dict)
    environment_policy: dict[str, str] = field(default_factory=dict)
    grading_policy: dict[str, str] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PublishPlatformVersionCommand:
    actor: Actor
    platform_id: str
    version_id: str
