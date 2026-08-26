"""Case and Prompt commands."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateCaseCommand:
    actor: Actor
    project_id: str
    name: str
    description: str = ""
    category: str = ""
    difficulty: str = ""
    language: str = ""
    tags: tuple[str, ...] = ()
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CreatePromptDraftVersionCommand:
    actor: Actor
    case_id: str
    content: str


@dataclass(frozen=True, slots=True)
class PublishPromptVersionCommand:
    actor: Actor
    case_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class CreateCaseDraftVersionCommand:
    actor: Actor
    case_id: str
    description: str
    repository_url: str
    commit_sha: str
    expected_checks: tuple[str, ...]
    applicable_grader_ids: tuple[str, ...]
    prompt_version_id: str
    subdirectory: str | None = None


@dataclass(frozen=True, slots=True)
class PublishCaseVersionCommand:
    actor: Actor
    case_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class DeprecateCaseCommand:
    actor: Actor
    case_id: str
