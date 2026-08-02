"""Agent and Adapter commands."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateAgentCommand:
    actor: Actor
    name: str
    description: str = ""
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CreateAgentDraftVersionCommand:
    actor: Actor
    agent_id: str
    label: str
    release_notes: str = ""


@dataclass(frozen=True, slots=True)
class PublishAgentVersionCommand:
    actor: Actor
    agent_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class CreateAdapterCommand:
    actor: Actor
    agent_id: str
    name: str
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CreateAdapterDraftVersionCommand:
    actor: Actor
    adapter_id: str
    label: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PublishAdapterVersionCommand:
    actor: Actor
    adapter_id: str
    version_id: str
