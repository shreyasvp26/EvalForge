"""Inbound models for the Event Persistence Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.normalized_model import NormalizedAction


@dataclass(frozen=True, slots=True)
class IncomingArtifact:
    """Artifact metadata ready for Application-mediated persistence.

    Object bytes are written by Infrastructure before this reaches the pipeline;
    the pipeline only records Domain metadata through Application.
    """

    run_id: RunId
    artifact_id: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    produced_by_grader_version_id: str | None = None


@dataclass(frozen=True, slots=True)
class IncomingExecutionEvent:
    """One Engine-emitted Execution Event awaiting durable recording."""

    run_id: RunId
    execution_event_id: str
    action: NormalizedAction
    artifact_ids: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PendingEvent:
    """Ordered buffer entry (emission order == persistence order)."""

    emission_index: int
    event: IncomingExecutionEvent
