"""Event Persistence Pipeline — durable recording via Application use cases.

Owns ordered buffering, idempotent write coordination, and projection hooks.
Does not execute Adapters, grade Runs, or write to repositories.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from agent_eval_application.commands.run import (
    RecordArtifactCommand,
    RecordExecutionEventCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO
from agent_eval_application.errors import ApplicationLayerError
from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.ndm_codec import action_to_payload

from agent_eval_workers.event_pipeline.errors import PersistenceFailure
from agent_eval_workers.event_pipeline.models import (
    IncomingArtifact,
    IncomingExecutionEvent,
    PendingEvent,
)
from agent_eval_workers.event_pipeline.ports import ApplicationEventWriter
from agent_eval_workers.event_pipeline.projector import ProjectionHub


@dataclass(slots=True)
class EventPersistencePipeline:
    """Transform Engine-emitted events into durable Domain records.

    Implements lifecycle ``EventPipelinePort.persist_final`` for end-of-stream
    flush of a Run's pending buffer.
    """

    writer: ApplicationEventWriter
    actor: Actor
    projections: ProjectionHub = field(default_factory=ProjectionHub)
    batch_size: int = 1
    """Flush when a run's pending event count reaches this size (>= 1)."""

    _emission_counter: int = field(default=0, init=False)
    _pending: dict[str, deque[PendingEvent]] = field(
        default_factory=lambda: defaultdict(deque),
        init=False,
    )
    _persisted_event_ids: set[str] = field(default_factory=set, init=False)
    _persisted_artifact_ids: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            msg = "batch_size must be >= 1"
            raise ValueError(msg)

    def submit_artifact(self, artifact: IncomingArtifact) -> ArtifactRecordDTO:
        """Persist Artifact metadata immediately (before dependent events)."""
        if artifact.artifact_id in self._persisted_artifact_ids:
            # Local short-circuit; Application remains source of truth on miss.
            record = self.writer.record_artifact(self._artifact_command(artifact))
            self.projections.notify_artifact(record)
            return record

        try:
            record = self.writer.record_artifact(self._artifact_command(artifact))
        except ApplicationLayerError as exc:
            raise PersistenceFailure(
                f"Artifact persistence failed for run {artifact.run_id.value}",
                run_id=artifact.run_id.value,
                code=getattr(exc, "code", "ARTIFACT_PERSISTENCE_FAILED"),
                retryable=getattr(exc, "retryable", True),
                cause=exc,
            ) from exc
        except Exception as exc:
            raise PersistenceFailure(
                f"Artifact persistence failed for run {artifact.run_id.value}",
                run_id=artifact.run_id.value,
                retryable=True,
                cause=exc,
            ) from exc

        self._persisted_artifact_ids.add(record.id)
        self.projections.notify_artifact(record)
        return record

    def submit_event(
        self, event: IncomingExecutionEvent
    ) -> list[ExecutionEventRecordDTO]:
        """Enqueue an event in emission order; auto-flush when batch is full."""
        if event.execution_event_id in self._persisted_event_ids:
            # Duplicate delivery after successful persist — no-op for ordering.
            return []

        pending = self._pending[event.run_id.value]
        self._emission_counter += 1
        pending.append(PendingEvent(emission_index=self._emission_counter, event=event))
        if len(pending) >= self.batch_size:
            return self.flush(event.run_id)
        return []

    def flush(self, run_id: RunId | None = None) -> list[ExecutionEventRecordDTO]:
        """Persist pending events in strict emission order.

        Stops at the first failure so history is never partially corrupted
        within a flush (already-acked items remain durable checkpoints).
        """
        if run_id is not None:
            return self._flush_run(run_id.value)

        recorded: list[ExecutionEventRecordDTO] = []
        for key in list(self._pending.keys()):
            recorded.extend(self._flush_run(key))
        return recorded

    def persist_final(self, run_id: RunId) -> None:
        """Lifecycle ``EventPipelinePort`` — flush remaining events for the Run."""
        self.flush(run_id)

    def pending_count(self, run_id: RunId) -> int:
        return len(self._pending.get(run_id.value, ()))

    def _flush_run(self, run_key: str) -> list[ExecutionEventRecordDTO]:
        pending = self._pending.get(run_key)
        if not pending:
            return []

        recorded: list[ExecutionEventRecordDTO] = []
        while pending:
            item = pending[0]
            event = item.event
            if event.execution_event_id in self._persisted_event_ids:
                pending.popleft()
                continue
            try:
                dto = self.writer.record_execution_event(self._event_command(event))
            except ApplicationLayerError as exc:
                raise PersistenceFailure(
                    f"Execution Event persistence failed for run {run_key}",
                    run_id=run_key,
                    code=getattr(exc, "code", "EVENT_PERSISTENCE_FAILED"),
                    retryable=getattr(exc, "retryable", True),
                    cause=exc,
                ) from exc
            except Exception as exc:
                raise PersistenceFailure(
                    f"Execution Event persistence failed for run {run_key}",
                    run_id=run_key,
                    retryable=True,
                    cause=exc,
                ) from exc

            pending.popleft()
            self._persisted_event_ids.add(dto.id)
            self.projections.notify_event(dto)
            recorded.append(dto)
        if not pending:
            self._pending.pop(run_key, None)
        return recorded

    def _event_command(
        self, event: IncomingExecutionEvent
    ) -> RecordExecutionEventCommand:
        return RecordExecutionEventCommand(
            actor=self.actor,
            run_id=event.run_id.value,
            execution_event_id=event.execution_event_id,
            action=action_to_payload(event.action),
            artifact_ids=event.artifact_ids,
            metadata=dict(event.metadata),
            occurred_at=event.occurred_at,
        )

    def _artifact_command(self, artifact: IncomingArtifact) -> RecordArtifactCommand:
        return RecordArtifactCommand(
            actor=self.actor,
            run_id=artifact.run_id.value,
            kind=artifact.kind,
            storage_key=artifact.storage_key,
            content_type=artifact.content_type,
            size_bytes=artifact.size_bytes,
            checksum=artifact.checksum,
            produced_by_grader_version_id=artifact.produced_by_grader_version_id,
            artifact_id=artifact.artifact_id,
        )


@dataclass(slots=True)
class UseCaseEventWriter:
    """Adapter from Application use cases to ``ApplicationEventWriter``."""

    record_event_uc: object
    record_artifact_uc: object

    def record_execution_event(
        self, command: RecordExecutionEventCommand
    ) -> ExecutionEventRecordDTO:
        return self.record_event_uc.execute(command)  # type: ignore[no-any-return]

    def record_artifact(self, command: RecordArtifactCommand) -> ArtifactRecordDTO:
        return self.record_artifact_uc.execute(command)  # type: ignore[no-any-return]
