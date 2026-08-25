"""Shared catalog resolution for run identity surfaces (no secrets)."""

from __future__ import annotations

from agent_eval_domain.common.ids import CaseVersionId, ProjectId

from agent_eval_application.dto.run import RunDTO
from agent_eval_application.ports.unit_of_work import UnitOfWork
from agent_eval_application.use_cases.base import with_domain_errors

# Mirror worker adapter registry keys without importing the worker package.
_ADAPTER_ALIASES: dict[str, str] = {
    "claude": "claude_code",
    "claude_code": "claude_code",
    "claude-code": "claude_code",
    "cursor": "cursor",
    "codex": "codex",
    "gemini": "gemini_cli",
    "gemini_cli": "gemini_cli",
    "gemini-cli": "gemini_cli",
    "aider": "aider",
}


def normalize_adapter_key(name: str) -> str | None:
    raw = name.strip().lower().replace(" ", "_").replace("-", "_")
    if raw in _ADAPTER_ALIASES:
        return _ADAPTER_ALIASES[raw]
    for token, key in (
        ("claude_code", "claude_code"),
        ("claude", "claude_code"),
        ("cursor", "cursor"),
        ("codex", "codex"),
        ("gemini", "gemini_cli"),
        ("aider", "aider"),
    ):
        if token in raw:
            return key
    return None


def resolve_repository(
    uow: UnitOfWork, dto: RunDTO
) -> tuple[str | None, str | None, str | None]:
    try:
        case_version = with_domain_errors(
            lambda: uow.cases.get_version(CaseVersionId(dto.pins.case_version_id))
        )
        repo = case_version.reference_repository
        return repo.repository_url, repo.commit_sha, repo.subdirectory
    except Exception:  # noqa: BLE001 — best-effort on catalog gaps
        return None, None, None


def resolve_agent_labels(uow: UnitOfWork, dto: RunDTO) -> tuple[str | None, str | None]:
    for agent in uow.agents.list_all():
        for version in agent.versions:
            if version.id.value == dto.pins.agent_version_id:
                return agent.name, version.label
    return None, None


def resolve_adapter_labels(
    uow: UnitOfWork, dto: RunDTO
) -> tuple[str | None, str | None, str | None]:
    for adapter in uow.adapters.list_all():
        for version in adapter.versions:
            if version.id.value == dto.pins.adapter_version_id:
                return adapter.name, version.label, normalize_adapter_key(adapter.name)
    return None, None, None


def resolve_prompt_version_label(uow: UnitOfWork, dto: RunDTO) -> str | None:
    for case in uow.cases.list_by_project(ProjectId(dto.pins.project_id)):
        for version in case.prompt.versions:
            if version.id.value == dto.pins.prompt_version_id:
                return f"v{version.version_number.value}"
    return None
