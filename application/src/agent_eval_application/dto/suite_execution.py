"""Suite execution DTOs — fan-out runs + deterministic aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.dto.run import RunDTO
from agent_eval_application.scoring.aggregation import ScoreAggregate


@dataclass(frozen=True, slots=True)
class SuiteRunEntryDTO:
    case_version_id: str
    position: int
    run: RunDTO
    aggregate: ScoreAggregate


@dataclass(frozen=True, slots=True)
class SuiteExecutionDTO:
    """Result of creating one Run per Suite composition entry."""

    suite_id: str
    suite_version_id: str
    execution_group_id: str
    total_cases: int
    runs: tuple[SuiteRunEntryDTO, ...]


@dataclass(frozen=True, slots=True)
class SuiteCaseResultDTO:
    case_version_id: str
    run_id: str
    status: str
    aggregate: ScoreAggregate
    failure_reason: str | None
    failure_category: str | None
    case_id: str | None = None
    case_name: str | None = None
    category: str | None = None
    difficulty: str | None = None


@dataclass(frozen=True, slots=True)
class SuiteAggregateDTO:
    """Deterministic suite rollup over Runs pinned to a SuiteVersion."""

    suite_id: str
    suite_version_id: str
    execution_group_id: str | None
    total_cases: int
    run_count: int
    completed: int
    failed: int
    """Runs with ``status == failed`` (platform/execution failure)."""
    execution_failed: int
    """Alias for ``failed`` — execution-time platform failures."""
    cancelled: int
    queued_or_running: int
    passed: int
    evaluation_failed: int
    """Completed runs where ``aggregate.passed`` is ``False``."""
    objective_failed_count: int
    """Cases where ``aggregate.objective_failed`` is ``True``."""
    pass_rate: float | None
    """Share of decided evaluation outcomes (``passed`` is not ``None``) that passed.

    Execution failures (``status == failed``) are excluded from the denominator so
    pass rate reflects grader outcomes, not hidden platform errors.
    """
    average_score: float | None
    cases: tuple[SuiteCaseResultDTO, ...]
