"""Event Persistence Pipeline tests — mocked Application writer only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from agent_eval_application.commands.run import (
    RecordArtifactCommand,
    RecordExecutionEventCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO
from agent_eval_application.errors import ApplicationLayerError
from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.normalized_model import MessageAction, ToolCallAction
from agent_eval_workers.event_pipeline import (
    EventPersistencePipeline,
    IncomingArtifact,
    IncomingExecutionEvent,
    PersistenceFailure,
    ProjectionHub,
)
from agent_eval_workers.event_pipeline.ports import EventProjector


@dataclass
class RecordingWriter:
    """Mock Application layer — ordered, idempotent, in-memory."""

    events: list[ExecutionEventRecordDTO] = field(default_factory=list)
    artifacts: list[ArtifactRecordDTO] = field(default_factory=list)
    _event_ids: dict[str, ExecutionEventRecordDTO] = field(default_factory=dict)
    _artifact_ids: dict[str, ArtifactRecordDTO] = field(default_factory=dict)
    _sequences: dict[str, int] = field(default_factory=dict)
    fail_on_event_id: str | None = None

    def record_execution_event(
        self, command: RecordExecutionEventCommand
    ) -> ExecutionEventRecordDTO:
        if self.fail_on_event_id == command.execution_event_id:
            raise ApplicationLayerError(
                "simulated persistence failure",
                code="SIMULATED_FAIL",
            )
        existing = self._event_ids.get(command.execution_event_id)
        if existing is not None:
            return ExecutionEventRecordDTO(
                id=existing.id,
                run_id=existing.run_id,
                sequence=existing.sequence,
                kind=existing.kind,
                artifact_ids=existing.artifact_ids,
                occurred_at=existing.occurred_at,
                already_recorded=True,
            )
        seq = self._sequences.get(command.run_id, 0)
        self._sequences[command.run_id] = seq + 1
        dto = ExecutionEventRecordDTO(
            id=command.execution_event_id,
            run_id=command.run_id,
            sequence=seq,
            kind=str(command.action["kind"]),
            artifact_ids=command.artifact_ids,
            occurred_at=command.occurred_at or datetime.now(tz=UTC),
            already_recorded=False,
        )
        self._event_ids[dto.id] = dto
        self.events.append(dto)
        return dto

    def record_artifact(self, command: RecordArtifactCommand) -> ArtifactRecordDTO:
        assert command.artifact_id is not None
        existing = self._artifact_ids.get(command.artifact_id)
        if existing is not None:
            return ArtifactRecordDTO(
                id=existing.id,
                run_id=existing.run_id,
                kind=existing.kind,
                storage_key=existing.storage_key,
                content_type=existing.content_type,
                size_bytes=existing.size_bytes,
                checksum=existing.checksum,
                already_recorded=True,
            )
        dto = ArtifactRecordDTO(
            id=command.artifact_id,
            run_id=command.run_id,
            kind=command.kind,
            storage_key=command.storage_key,
            content_type=command.content_type,
            size_bytes=command.size_bytes,
            checksum=command.checksum,
            already_recorded=False,
        )
        self._artifact_ids[dto.id] = dto
        self.artifacts.append(dto)
        return dto


@dataclass
class RecordingProjector:
    events: list[ExecutionEventRecordDTO] = field(default_factory=list)
    artifacts: list[ArtifactRecordDTO] = field(default_factory=list)

    def on_event_persisted(self, record: ExecutionEventRecordDTO) -> None:
        self.events.append(record)

    def on_artifact_persisted(self, record: ArtifactRecordDTO) -> None:
        self.artifacts.append(record)


def _pipeline(
    *,
    batch_size: int = 1,
    writer: RecordingWriter | None = None,
    projector: EventProjector | None = None,
) -> tuple[EventPersistencePipeline, RecordingWriter, RecordingProjector]:
    w = writer or RecordingWriter()
    hub = ProjectionHub()
    proj = projector or RecordingProjector()
    hub.subscribe(proj)  # type: ignore[arg-type]
    pipe = EventPersistencePipeline(
        writer=w,
        actor=Actor(id="worker"),
        projections=hub,
        batch_size=batch_size,
    )
    return pipe, w, proj  # type: ignore[return-value]


def _event(
    run: str,
    eid: str,
    *,
    artifacts: tuple[str, ...] = (),
) -> IncomingExecutionEvent:
    return IncomingExecutionEvent(
        run_id=RunId(run),
        execution_event_id=eid,
        action=MessageAction(role="assistant", content_summary=eid),
        artifact_ids=artifacts,
    )


def test_ordered_persistence() -> None:
    pipe, writer, proj = _pipeline(batch_size=10)
    run = "run-1"
    for i in range(5):
        pipe.submit_event(_event(run, f"e-{i}"))
    recorded = pipe.flush(RunId(run))
    assert [r.sequence for r in recorded] == [0, 1, 2, 3, 4]
    assert [r.id for r in writer.events] == [f"e-{i}" for i in range(5)]
    assert [r.id for r in proj.events] == [f"e-{i}" for i in range(5)]


def test_duplicate_deliveries_are_idempotent() -> None:
    pipe, writer, _proj = _pipeline(batch_size=1)
    ev = _event("run-1", "e-1")
    pipe.submit_event(ev)
    pipe.submit_event(ev)  # duplicate after persist — local no-op
    pipe.submit_event(ev)
    assert len(writer.events) == 1
    # Application-level replay
    again = writer.record_execution_event(
        RecordExecutionEventCommand(
            actor=Actor(id="worker"),
            run_id="run-1",
            execution_event_id="e-1",
            action={"kind": "message", "role": "assistant", "content_summary": "e-1"},
        )
    )
    assert again.already_recorded is True
    assert len(writer.events) == 1


def test_append_only_sequences_never_reuse() -> None:
    pipe, writer, _proj = _pipeline()
    pipe.submit_event(_event("run-1", "e-0"))
    pipe.submit_event(_event("run-1", "e-1"))
    assert writer.events[0].sequence == 0
    assert writer.events[1].sequence == 1
    # Replaying e-0 does not create sequence 2 or mutate e-0
    replay = writer.record_execution_event(
        RecordExecutionEventCommand(
            actor=Actor(id="worker"),
            run_id="run-1",
            execution_event_id="e-0",
            action={"kind": "message", "role": "assistant", "content_summary": "e-0"},
        )
    )
    assert replay.sequence == 0
    assert replay.already_recorded is True
    assert len(writer.events) == 2


def test_artifact_persistence_before_referencing_event() -> None:
    pipe, writer, proj = _pipeline()
    art = IncomingArtifact(
        run_id=RunId("run-1"),
        artifact_id="art-1",
        kind="diff",
        storage_key="s3://bucket/art-1",
        content_type="text/plain",
        size_bytes=12,
        checksum="abc",
    )
    recorded_art = pipe.submit_artifact(art)
    assert recorded_art.already_recorded is False
    pipe.submit_event(_event("run-1", "e-1", artifacts=("art-1",)))
    assert writer.artifacts[0].id == "art-1"
    assert writer.events[0].artifact_ids == ("art-1",)
    assert proj.artifacts[0].id == "art-1"


def test_artifact_idempotent_replay() -> None:
    pipe, writer, _proj = _pipeline()
    art = IncomingArtifact(
        run_id=RunId("run-1"),
        artifact_id="art-1",
        kind="log",
        storage_key="s3://bucket/art-1",
        content_type="text/plain",
        size_bytes=1,
        checksum="x",
    )
    pipe.submit_artifact(art)
    again = pipe.submit_artifact(art)
    assert again.already_recorded is True
    assert len(writer.artifacts) == 1


def test_batching_flushes_at_batch_size() -> None:
    pipe, writer, _proj = _pipeline(batch_size=3)
    pipe.submit_event(_event("run-1", "e-0"))
    pipe.submit_event(_event("run-1", "e-1"))
    assert writer.events == []
    pipe.submit_event(_event("run-1", "e-2"))
    assert [e.id for e in writer.events] == ["e-0", "e-1", "e-2"]


def test_persist_final_flushes_remainder() -> None:
    pipe, writer, _proj = _pipeline(batch_size=10)
    pipe.submit_event(_event("run-1", "e-0"))
    pipe.submit_event(_event("run-1", "e-1"))
    assert writer.events == []
    pipe.persist_final(RunId("run-1"))
    assert [e.id for e in writer.events] == ["e-0", "e-1"]
    assert pipe.pending_count(RunId("run-1")) == 0


def test_persistence_failure_stops_flush_without_skipping() -> None:
    writer = RecordingWriter(fail_on_event_id="e-1")
    pipe, writer, _proj = _pipeline(batch_size=10, writer=writer)
    pipe.submit_event(_event("run-1", "e-0"))
    pipe.submit_event(_event("run-1", "e-1"))
    pipe.submit_event(_event("run-1", "e-2"))
    with pytest.raises(PersistenceFailure) as exc_info:
        pipe.flush(RunId("run-1"))
    assert exc_info.value.retryable is False
    assert [e.id for e in writer.events] == ["e-0"]
    # e-1 and e-2 remain pending — not skipped / corrupted
    assert pipe.pending_count(RunId("run-1")) == 2


def test_worker_restart_replay_via_application_idempotency() -> None:
    """Simulate restart: new pipeline, same Application (durable) state."""
    shared = RecordingWriter()
    pipe1, _, _ = _pipeline(writer=shared)
    pipe1.submit_event(_event("run-1", "e-0"))
    pipe1.submit_event(
        IncomingExecutionEvent(
            run_id=RunId("run-1"),
            execution_event_id="e-1",
            action=ToolCallAction(tool_name="read", arguments={"path": "a"}),
        )
    )

    # Restart loses in-memory pipeline state; Application still has records.
    pipe2, _, proj2 = _pipeline(writer=shared)
    # Replay both ids — Application returns already_recorded
    pipe2.submit_event(_event("run-1", "e-0"))
    pipe2.submit_event(
        IncomingExecutionEvent(
            run_id=RunId("run-1"),
            execution_event_id="e-1",
            action=ToolCallAction(tool_name="read", arguments={"path": "a"}),
        )
    )
    assert len(shared.events) == 2
    assert all(e.already_recorded is False for e in shared.events)
    # Second pipeline notified on Application responses (including replay)
    assert len(proj2.events) == 2
    assert all(e.already_recorded for e in proj2.events)


def test_projection_notifications() -> None:
    pipe, _writer, proj = _pipeline()
    pipe.submit_artifact(
        IncomingArtifact(
            run_id=RunId("run-1"),
            artifact_id="art-1",
            kind="stdout",
            storage_key="k",
            content_type="text/plain",
            size_bytes=0,
            checksum="0",
        )
    )
    pipe.submit_event(_event("run-1", "e-1", artifacts=("art-1",)))
    assert len(proj.artifacts) == 1
    assert len(proj.events) == 1
