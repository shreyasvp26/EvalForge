"""Build inspectable Run provenance from pinned versions + catalogs."""

from __future__ import annotations

from agent_eval_domain.common.ids import (
    CaseVersionId,
    RunId,
)

from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.provenance import RunProvenanceDTO
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetRunProvenanceQuery
from agent_eval_application.scoring.aggregation import aggregate_scores
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


def _normalize_adapter_key(name: str) -> str | None:
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


class GetRunProvenance:
    """Assemble complete evaluation identity for a Run (no secrets)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetRunProvenanceQuery) -> RunProvenanceDTO:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            dto = RunDTO.from_domain(run)

            case_version = None
            repository_url = None
            commit_sha = None
            subdirectory = None
            try:
                case_version = with_domain_errors(
                    lambda: uow.cases.get_version(
                        CaseVersionId(dto.pins.case_version_id)
                    )
                )
                repository_url = case_version.reference_repository.repository_url
                commit_sha = case_version.reference_repository.commit_sha
                subdirectory = case_version.reference_repository.subdirectory
            except Exception:  # noqa: BLE001 — provenance best-effort on catalog gaps
                pass

            agent_name = None
            agent_version_label = None
            adapter_name = None
            adapter_version_label = None
            adapter_key = None

            # Resolve agent/adapter by scanning catalogs for matching version ids.
            for agent in uow.agents.list_all():
                for version in agent.versions:
                    if version.id.value == dto.pins.agent_version_id:
                        agent_name = agent.name
                        agent_version_label = version.label
                        break
                if agent_name is not None:
                    break

            for adapter in uow.adapters.list_all():
                for version in adapter.versions:
                    if version.id.value == dto.pins.adapter_version_id:
                        adapter_name = adapter.name
                        adapter_version_label = version.label
                        adapter_key = _normalize_adapter_key(adapter.name)
                        break
                if adapter_name is not None:
                    break

            grader_summaries: list[dict[str, object]] = []
            for grader in uow.graders.list_all():
                for version in grader.versions:
                    if version.id.value in dto.pins.grader_version_ids:
                        grader_summaries.append(
                            {
                                "grader_id": grader.id.value,
                                "grader_name": grader.name,
                                "family": grader.family.value,
                                "grader_version_id": version.id.value,
                                "label": version.label,
                            }
                        )

            # Preserve pin order.
            order = {vid: idx for idx, vid in enumerate(dto.pins.grader_version_ids)}
            grader_summaries.sort(
                key=lambda row: order.get(str(row["grader_version_id"]), 10_000)
            )

            aggregate = aggregate_scores(dto.scores)
            return RunProvenanceDTO(
                run_id=dto.id,
                status=dto.status,
                created_at=dto.created_at,
                failure_reason=dto.failure_reason,
                cancellation_reason=dto.cancellation_reason,
                project_id=dto.pins.project_id,
                case_version_id=dto.pins.case_version_id,
                prompt_version_id=dto.pins.prompt_version_id,
                agent_version_id=dto.pins.agent_version_id,
                adapter_version_id=dto.pins.adapter_version_id,
                platform_version_id=dto.pins.platform_version_id,
                grader_version_ids=dto.pins.grader_version_ids,
                suite_version_id=dto.pins.suite_version_id,
                repository_url=repository_url,
                commit_sha=commit_sha,
                subdirectory=subdirectory,
                agent_name=agent_name,
                agent_version_label=agent_version_label,
                adapter_name=adapter_name,
                adapter_version_label=adapter_version_label,
                adapter_key=adapter_key,
                grader_summaries=tuple(grader_summaries),
                score_aggregate=aggregate,
                expected_grader_count=dto.expected_grader_count,
                produced_score_count=dto.produced_score_count,
                is_partially_graded=dto.is_partially_graded,
            )
