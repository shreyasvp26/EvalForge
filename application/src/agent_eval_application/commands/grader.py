"""Grader commands."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateGraderCommand:
    actor: Actor
    name: str
    family: str
    description: str = ""
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CreateGraderDraftVersionCommand:
    actor: Actor
    grader_id: str
    label: str
    specification: str


@dataclass(frozen=True, slots=True)
class PublishGraderVersionCommand:
    actor: Actor
    grader_id: str
    version_id: str
