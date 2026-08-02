"""Ports for Application recording and live projection subscribers."""

from __future__ import annotations

from typing import Protocol

from agent_eval_application.commands.run import (
    RecordArtifactCommand,
    RecordExecutionEventCommand,
)
from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO


class ApplicationEventWriter(Protocol):
    """Narrow Application surface used by the pipeline (mocked in tests).

    Implementations wrap ``RecordExecutionEvent`` / ``RecordArtifact`` use cases.
    The pipeline never talks to repositories.
    """

    def record_execution_event(
        self, command: RecordExecutionEventCommand
    ) -> ExecutionEventRecordDTO: ...

    def record_artifact(self, command: RecordArtifactCommand) -> ArtifactRecordDTO: ...


class EventProjector(Protocol):
    """Subscriber hook for future SSE / WebSocket / dashboard projections.

    Networking is out of scope — projectors only observe durable records.
    """

    def on_event_persisted(self, record: ExecutionEventRecordDTO) -> None: ...

    def on_artifact_persisted(self, record: ArtifactRecordDTO) -> None: ...
