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
    total_cases: int
    runs: tuple[SuiteRunEntryDTO, ...]


@dataclass(frozen=True, slots=True)
class SuiteCaseResultDTO:
    case_version_id: str
    run_id: str
    status: str
    aggregate: ScoreAggregate
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class SuiteAggregateDTO:
    """Deterministic suite rollup over Runs pinned to a SuiteVersion."""

    suite_id: str
    suite_version_id: str
    total_cases: int
    run_count: int
    completed: int
    failed: int
    cancelled: int
    queued_or_running: int
    passed: int
    pass_rate: float | None
    average_score: float | None
    cases: tuple[SuiteCaseResultDTO, ...]
