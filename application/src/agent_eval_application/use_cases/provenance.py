"""Build inspectable Run provenance from pinned versions + catalogs."""

from __future__ import annotations

from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.ids import PlatformVersionId, RunId

from agent_eval_application.benchmark import benchmark_identity_from_run
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.provenance import ReproducibilityDTO, RunProvenanceDTO
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetRunProvenanceQuery
from agent_eval_application.run_identity import (
    resolve_adapter_labels,
    resolve_agent_labels,
    resolve_repository,
)
from agent_eval_application.scoring.aggregation import aggregate_scores
from agent_eval_application.use_cases.base import with_domain_errors


def _build_reproducibility(
    dto: RunDTO,
    *,
    repository_url: str | None,
    commit_sha: str | None,
) -> ReproducibilityDTO:
    missing: list[str] = []
    if not (repository_url and repository_url.strip()):
        missing.append("repository_url")
    if not (commit_sha and commit_sha.strip()):
        missing.append("commit_sha")
    pin_checks = (
        ("project_id", dto.pins.project_id),
        ("case_version_id", dto.pins.case_version_id),
        ("prompt_version_id", dto.pins.prompt_version_id),
        ("agent_version_id", dto.pins.agent_version_id),
        ("adapter_version_id", dto.pins.adapter_version_id),
        ("platform_version_id", dto.pins.platform_version_id),
    )
    for label, value in pin_checks:
        if not str(value).strip():
            missing.append(label)
    if not dto.pins.grader_version_ids:
        missing.append("grader_version_ids")

    can_reproduce = not missing
    notes = (
        "All repository pins and version pins are present for reproduction."
        if can_reproduce
        else "Missing inputs prevent a faithful re-run with current pins."
    )
    return ReproducibilityDTO(
        can_reproduce=can_reproduce,
        missing=tuple(missing),
        notes=notes,
    )


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

            repository_url, commit_sha, subdirectory = resolve_repository(uow, dto)
            agent_name, agent_version_label = resolve_agent_labels(uow, dto)
            adapter_name, adapter_version_label, adapter_key = resolve_adapter_labels(
                uow, dto
            )
            platform_name = None
            platform_version_label = None
            platform_policy_summaries: dict[str, dict[str, str]] = {}
            try:
                platform_version = uow.platforms.get_version(
                    PlatformVersionId(dto.pins.platform_version_id)
                )
                platform_version_label = platform_version.label
                platform = uow.platforms.get(platform_version.platform_id)
                platform_name = platform.name
                platform_policy_summaries = {
                    "sandbox": dict(platform_version.sandbox_policy),
                    "execution": dict(platform_version.execution_policy),
                    "timeout": dict(platform_version.timeout_policy),
                    "environment": dict(platform_version.environment_policy),
                    "grading": dict(platform_version.grading_policy),
                }
            except NotFoundError:
                # Historical runs may predate the catalog migration.
                pass

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

            order = {vid: idx for idx, vid in enumerate(dto.pins.grader_version_ids)}
            grader_summaries.sort(
                key=lambda row: order.get(str(row["grader_version_id"]), 10_000)
            )

            aggregate = aggregate_scores(dto.scores)
            identity = benchmark_identity_from_run(
                dto,
                repository_url=repository_url,
                commit_sha=commit_sha,
            )
            return RunProvenanceDTO(
                run_id=dto.id,
                status=dto.status,
                created_at=dto.created_at,
                failure_reason=dto.failure_reason,
                failure_category=dto.failure_category,
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
                platform_name=platform_name,
                platform_version_label=platform_version_label,
                platform_policy_summaries=platform_policy_summaries,
                grader_summaries=tuple(grader_summaries),
                score_aggregate=aggregate,
                expected_grader_count=dto.expected_grader_count,
                produced_score_count=dto.produced_score_count,
                is_partially_graded=dto.is_partially_graded,
                telemetry=dto.telemetry,
                event_count=len(run.execution_events),
                artifact_count=len(run.artifacts),
                execution_mode=dto.execution_mode,
                execution_metadata=dict(dto.execution_metadata),
                benchmark_key=identity.benchmark_key,
                suite_version_id_as_benchmark=dto.pins.suite_version_id,
                reproducibility=_build_reproducibility(
                    dto,
                    repository_url=repository_url,
                    commit_sha=commit_sha,
                ),
            )
