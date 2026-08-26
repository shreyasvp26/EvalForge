"""Benchmark evaluation matrix — cross-agent scores on a shared definition."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.commands.run_comparison import CompareRunsCommand
from agent_eval_application.dto.run_comparison import RunComparisonResultDTO
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.use_cases.run_comparison import CompareRuns


@dataclass(frozen=True, slots=True)
class BenchmarkMatrixCellDTO:
    adapter_key: str | None
    adapter_name: str | None
    execution_mode: str | None
    run_id: str
    status: str
    overall_score: float | None
    passed: bool | None
    duration_ms: int | None
    failure_category: str | None


@dataclass(frozen=True, slots=True)
class BenchmarkMatrixDTO:
    benchmark_key: str | None
    comparable: bool
    notes: str
    cells: tuple[BenchmarkMatrixCellDTO, ...]
    mismatches: tuple[str, ...]


class BuildBenchmarkMatrix:
    """Build an adapter × score matrix when runs share a benchmark definition."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        compare_runs: CompareRuns | None = None,
    ) -> None:
        self._compare = compare_runs or CompareRuns(uow_factory, auth)

    def execute(self, command: CompareRunsCommand) -> BenchmarkMatrixDTO:
        comparison: RunComparisonResultDTO = self._compare.execute(command)
        if not comparison.comparability.compatible:
            return BenchmarkMatrixDTO(
                benchmark_key=None,
                comparable=False,
                notes=comparison.comparability.notes,
                cells=(),
                mismatches=comparison.comparability.mismatches,
            )

        cells: list[BenchmarkMatrixCellDTO] = []
        for entry in comparison.runs:
            cells.append(
                BenchmarkMatrixCellDTO(
                    adapter_key=entry.adapter_key,
                    adapter_name=entry.adapter_name,
                    execution_mode=entry.execution_mode,
                    run_id=entry.run_id,
                    status=entry.status,
                    overall_score=entry.score_aggregate.overall_score,
                    passed=entry.score_aggregate.passed,
                    duration_ms=entry.duration_ms,
                    failure_category=entry.failure_category,
                )
            )

        synthetic = any(c.execution_mode == "deterministic" for c in cells)
        notes = comparison.comparability.notes
        if synthetic:
            notes = (
                f"{notes} Warning: matrix includes deterministic/synthetic runs; "
                "those scores are not live coding-agent results."
            )

        return BenchmarkMatrixDTO(
            benchmark_key=comparison.comparability.benchmark_key,
            comparable=True,
            notes=notes,
            cells=tuple(cells),
            mismatches=(),
        )
