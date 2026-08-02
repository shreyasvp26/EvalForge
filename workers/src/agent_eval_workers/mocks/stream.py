"""Narrow stream sink Adapters write into (EventPersistencePipeline satisfies this)."""

from __future__ import annotations

from typing import Protocol

from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO

from agent_eval_workers.event_pipeline.models import (
    IncomingArtifact,
    IncomingExecutionEvent,
)


class EventStreamPort(Protocol):
    """Continuous event/artifact intake during Adapter execution."""

    def submit_artifact(self, artifact: IncomingArtifact) -> ArtifactRecordDTO: ...

    def submit_event(
        self, event: IncomingExecutionEvent
    ) -> list[ExecutionEventRecordDTO]: ...
