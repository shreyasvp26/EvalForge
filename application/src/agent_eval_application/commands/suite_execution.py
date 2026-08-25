"""Suite execution commands."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateSuiteRunsCommand:
    """Create and enqueue one EvaluationRun per published Suite composition entry."""

    actor: Actor
    suite_id: str
    suite_version_id: str
    agent_id: str
    agent_version_id: str
    adapter_version_id: str
    platform_version_id: str
    grader_version_refs: tuple[tuple[str, str], ...] | None = None
    """Optional shared grader pins; default = each case's applicable active graders."""
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class AggregateSuiteResultsCommand:
    actor: Actor
    suite_id: str
    suite_version_id: str
