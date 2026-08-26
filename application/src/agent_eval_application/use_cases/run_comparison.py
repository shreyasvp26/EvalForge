"""Compare multiple Runs side-by-side with explicit benchmark comparability."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId

from agent_eval_application.benchmark import (
    AGENT_COMPARISON_DIMENSIONS,
    BENCHMARK_COMPARABILITY_DIMENSIONS,
    benchmark_identity_from_run,
)
from agent_eval_application.commands.run_comparison import CompareRunsCommand
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.dto.run_comparison import (
    RunComparabilityDTO,
    RunComparisonDeltaDTO,
    RunComparisonEntryDTO,
    RunComparisonResultDTO,
)
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.run_identity import (
    resolve_adapter_labels,
    resolve_agent_labels,
    resolve_prompt_version_label,
    resolve_repository,
)
from agent_eval_application.scoring.aggregation import aggregate_scores
from agent_eval_application.use_cases.base import with_domain_errors

_MAX_COMPARE_RUNS = 5
_MIN_COMPARE_RUNS = 2

_PIN_FIELDS = (
    ("project_id", "project_id"),
    ("case_version_id", "case_version_id"),
    ("prompt_version_id", "prompt_version_id"),
    ("agent_version_id", "agent_version_id"),
    ("adapter_version_id", "adapter_version_id"),
    ("platform_version_id", "platform_version_id"),
    ("suite_version_id", "suite_version_id"),
)


def _pin_differences(baseline: RunDTO, other: RunDTO) -> tuple[str, ...]:
    diffs: list[str] = []
    for attr, label in _PIN_FIELDS:
        base_val = getattr(baseline.pins, attr)
        other_val = getattr(other.pins, attr)
        if base_val != other_val:
            diffs.append(f"{label}: {base_val!r} → {other_val!r}")
    if baseline.pins.grader_version_ids != other.pins.grader_version_ids:
        diffs.append(
            "grader_version_ids: "
            f"{list(baseline.pins.grader_version_ids)!r} → "
            f"{list(other.pins.grader_version_ids)!r}"
        )
    return tuple(diffs)


def _comparability(
    baseline: RunComparisonEntryDTO,
    others: tuple[RunComparisonEntryDTO, ...],
    *,
    baseline_dto: RunDTO,
    other_dtos: tuple[RunDTO, ...],
) -> RunComparabilityDTO:
    baseline_identity = benchmark_identity_from_run(
        baseline_dto,
        repository_url=baseline.repository_url,
        commit_sha=baseline.commit_sha,
    )
    mismatches: list[str] = []
    expected_diffs: list[str] = []

    for entry, dto in zip(others, other_dtos, strict=True):
        identity = benchmark_identity_from_run(
            dto,
            repository_url=entry.repository_url,
            commit_sha=entry.commit_sha,
        )
        if identity.case_version_id != baseline_identity.case_version_id:
            mismatches.append(
                f"{entry.run_id}: case_version_id "
                f"{baseline_identity.case_version_id!r} → {identity.case_version_id!r}"
            )
        if identity.prompt_version_id != baseline_identity.prompt_version_id:
            mismatches.append(
                f"{entry.run_id}: prompt_version_id "
                f"{baseline_identity.prompt_version_id!r} → "
                f"{identity.prompt_version_id!r}"
            )
        if identity.platform_version_id != baseline_identity.platform_version_id:
            mismatches.append(
                f"{entry.run_id}: platform_version_id "
                f"{baseline_identity.platform_version_id!r} → "
                f"{identity.platform_version_id!r}"
            )
        if identity.grader_version_ids != baseline_identity.grader_version_ids:
            mismatches.append(
                f"{entry.run_id}: grader_version_ids differ from baseline"
            )
        if (identity.repository_url or "") != (baseline_identity.repository_url or ""):
            mismatches.append(f"{entry.run_id}: repository_url differs from baseline")
        if (identity.commit_sha or "") != (baseline_identity.commit_sha or ""):
            mismatches.append(
                f"{entry.run_id}: commit_sha "
                f"{baseline_identity.commit_sha!r} → {identity.commit_sha!r}"
            )

        if dto.pins.agent_version_id != baseline_dto.pins.agent_version_id:
            expected_diffs.append(
                f"{entry.run_id}: agent_version_id "
                f"{baseline_dto.pins.agent_version_id!r} → "
                f"{dto.pins.agent_version_id!r}"
            )
        if dto.pins.adapter_version_id != baseline_dto.pins.adapter_version_id:
            expected_diffs.append(
                f"{entry.run_id}: adapter_version_id "
                f"{baseline_dto.pins.adapter_version_id!r} → "
                f"{dto.pins.adapter_version_id!r}"
            )
        if entry.adapter_key != baseline.adapter_key:
            expected_diffs.append(
                f"{entry.run_id}: adapter_key "
                f"{baseline.adapter_key!r} → {entry.adapter_key!r}"
            )
        if entry.execution_mode != baseline.execution_mode:
            expected_diffs.append(
                f"{entry.run_id}: execution_mode "
                f"{baseline.execution_mode!r} → {entry.execution_mode!r}"
            )

    compatible = not mismatches
    notes = (
        "Runs share benchmark dimensions (case, SHA, prompt, graders, platform); "
        "agent/adapter/execution_mode differences are expected for cross-agent "
        "comparison."
        if compatible
        else "Runs are not comparable as the same benchmark — mismatches listed. "
        "Do not treat score deltas as fair agent comparison."
    )
    return RunComparabilityDTO(
        compatible=compatible,
        shared_dimensions=BENCHMARK_COMPARABILITY_DIMENSIONS,
        agent_difference_dimensions=AGENT_COMPARISON_DIMENSIONS,
        mismatches=tuple(mismatches),
        expected_agent_differences=tuple(expected_diffs),
        benchmark_key=baseline_identity.benchmark_key if compatible else None,
        notes=notes,
    )


class CompareRuns:
    """Compare 2–5 Runs the actor can access."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, command: CompareRunsCommand) -> RunComparisonResultDTO:
        if not command.run_ids:
            raise ApplicationValidationError(
                "At least two run_ids are required",
                code="COMPARE_RUNS_TOO_FEW",
            )
        if len(command.run_ids) < _MIN_COMPARE_RUNS:
            raise ApplicationValidationError(
                f"At least {_MIN_COMPARE_RUNS} run_ids are required",
                code="COMPARE_RUNS_TOO_FEW",
            )
        if len(command.run_ids) > _MAX_COMPARE_RUNS:
            raise ApplicationValidationError(
                f"At most {_MAX_COMPARE_RUNS} run_ids are allowed",
                code="COMPARE_RUNS_TOO_MANY",
                details={"max": _MAX_COMPARE_RUNS},
            )
        if len(set(command.run_ids)) != len(command.run_ids):
            raise ApplicationValidationError(
                "run_ids must be unique",
                code="COMPARE_RUNS_DUPLICATE",
            )

        run_ids = tuple(
            RunId(require_non_empty(rid, field="run_id")) for rid in command.run_ids
        )
        entries: list[RunComparisonEntryDTO] = []
        dtos: list[RunDTO] = []

        with self._uow_factory() as uow:
            for run_id in run_ids:
                run = with_domain_errors(lambda rid=run_id: uow.runs.get(rid))
                self._auth.ensure_can_access_project(command.actor, run.pins.project_id)
                dto = RunDTO.from_domain(run)
                dtos.append(dto)
                repository_url, commit_sha, _subdir = resolve_repository(uow, dto)
                _agent_name, agent_version = resolve_agent_labels(uow, dto)
                adapter_name, _adapter_label, adapter_key = resolve_adapter_labels(
                    uow, dto
                )
                prompt_version = resolve_prompt_version_label(uow, dto)
                aggregate = aggregate_scores(dto.scores)
                telem = dto.telemetry
                duration_ms = telem.wall_clock_ms if telem.wall_clock_ms else None
                identity = benchmark_identity_from_run(
                    dto,
                    repository_url=repository_url,
                    commit_sha=commit_sha,
                )
                entries.append(
                    RunComparisonEntryDTO(
                        run_id=dto.id,
                        status=dto.status,
                        failure_reason=dto.failure_reason,
                        failure_category=dto.failure_category,
                        pins=dto.pins,
                        repository_url=repository_url,
                        commit_sha=commit_sha,
                        adapter_key=adapter_key,
                        adapter_name=adapter_name,
                        prompt_version=prompt_version,
                        agent_version=agent_version,
                        telemetry=telem,
                        score_aggregate=aggregate,
                        duration_ms=duration_ms,
                        execution_mode=dto.execution_mode,
                        benchmark_key=identity.benchmark_key,
                        suite_version_id=dto.pins.suite_version_id,
                    )
                )

        baseline = dtos[0]
        baseline_agg = entries[0].score_aggregate
        deltas: list[RunComparisonDeltaDTO] = []
        for dto, entry in zip(dtos[1:], entries[1:], strict=True):
            score_delta = None
            if (
                baseline_agg.overall_score is not None
                and entry.score_aggregate.overall_score is not None
            ):
                score_delta = (
                    entry.score_aggregate.overall_score - baseline_agg.overall_score
                )
            pass_changed = None
            if (
                baseline_agg.passed is not None
                and entry.score_aggregate.passed is not None
            ):
                pass_changed = baseline_agg.passed != entry.score_aggregate.passed
            duration_delta = None
            if entries[0].duration_ms is not None and entry.duration_ms is not None:
                duration_delta = entry.duration_ms - entries[0].duration_ms
            deltas.append(
                RunComparisonDeltaDTO(
                    run_id=entry.run_id,
                    score_delta=score_delta,
                    pass_changed=pass_changed,
                    duration_delta_ms=duration_delta,
                    pin_differences=_pin_differences(baseline, dto),
                )
            )

        comparability = _comparability(
            entries[0],
            tuple(entries[1:]),
            baseline_dto=baseline,
            other_dtos=tuple(dtos[1:]),
        )

        return RunComparisonResultDTO(
            baseline_run_id=entries[0].run_id,
            runs=tuple(entries),
            deltas=tuple(deltas),
            comparability=comparability,
        )
