"""Run comparison DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.dto.run import RunPinsDTO, RunTelemetryDTO
from agent_eval_application.scoring.aggregation import ScoreAggregate


@dataclass(frozen=True, slots=True)
class RunComparisonEntryDTO:
    run_id: str
    status: str
    failure_reason: str | None
    failure_category: str | None
    pins: RunPinsDTO
    repository_url: str | None
    commit_sha: str | None
    adapter_key: str | None
    adapter_name: str | None
    prompt_version: str | None
    agent_version: str | None
    telemetry: RunTelemetryDTO
    score_aggregate: ScoreAggregate
    duration_ms: int | None
    execution_mode: str | None = None
    benchmark_key: str | None = None
    suite_version_id: str | None = None
    provider_key: str | None = None
    gateway_key: str | None = None
    requested_model: str | None = None
    routing_mode: str | None = None
    canonical_evaluation: bool | None = None


@dataclass(frozen=True, slots=True)
class RunComparisonDeltaDTO:
    run_id: str
    score_delta: float | None
    pass_changed: bool | None
    duration_delta_ms: int | None
    pin_differences: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunComparabilityDTO:
    """Whether compared runs share the same benchmark definition."""

    compatible: bool
    shared_dimensions: tuple[str, ...]
    agent_difference_dimensions: tuple[str, ...]
    mismatches: tuple[str, ...]
    expected_agent_differences: tuple[str, ...]
    benchmark_key: str | None
    notes: str


@dataclass(frozen=True, slots=True)
class RunComparisonResultDTO:
    baseline_run_id: str
    runs: tuple[RunComparisonEntryDTO, ...]
    deltas: tuple[RunComparisonDeltaDTO, ...]
    comparability: RunComparabilityDTO
