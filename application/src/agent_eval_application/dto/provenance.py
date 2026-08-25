"""Run provenance — inspectable evaluation identity without secrets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_application.dto.run import RunTelemetryDTO
from agent_eval_application.scoring.aggregation import ScoreAggregate


@dataclass(frozen=True, slots=True)
class ReproducibilityDTO:
    """Whether the pinned evaluation can be re-run without missing inputs."""

    can_reproduce: bool
    missing: tuple[str, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class RunProvenanceDTO:
    """Everything needed to answer: what exactly did this Run evaluate?"""

    run_id: str
    status: str
    created_at: datetime
    failure_reason: str | None
    failure_category: str | None
    cancellation_reason: str | None

    project_id: str
    case_version_id: str
    prompt_version_id: str
    agent_version_id: str
    adapter_version_id: str
    platform_version_id: str
    grader_version_ids: tuple[str, ...]
    suite_version_id: str | None

    repository_url: str | None
    commit_sha: str | None
    subdirectory: str | None

    agent_name: str | None
    agent_version_label: str | None
    adapter_name: str | None
    adapter_version_label: str | None
    adapter_key: str | None
    grader_summaries: tuple[dict[str, object], ...]
    score_aggregate: ScoreAggregate
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool

    telemetry: RunTelemetryDTO
    event_count: int
    artifact_count: int
    execution_mode: str | None
    execution_metadata: dict[str, str]
    reproducibility: ReproducibilityDTO
    platform_name: str | None = None
    platform_version_label: str | None = None
    platform_policy_summaries: dict[str, dict[str, str]] = field(default_factory=dict)
