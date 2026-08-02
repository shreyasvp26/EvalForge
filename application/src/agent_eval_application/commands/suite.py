"""Suite commands."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateSuiteCommand:
    actor: Actor
    project_id: str
    name: str
    description: str = ""
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class SuiteCompositionEntryInput:
    case_version_id: str
    position: int
    case_project_id: str


@dataclass(frozen=True, slots=True)
class CreateSuiteDraftVersionCommand:
    actor: Actor
    suite_id: str
    composition: tuple[SuiteCompositionEntryInput, ...]


@dataclass(frozen=True, slots=True)
class PublishSuiteVersionCommand:
    actor: Actor
    suite_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class RetireSuiteVersionCommand:
    actor: Actor
    suite_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class DeprecateSuiteCommand:
    actor: Actor
    suite_id: str
