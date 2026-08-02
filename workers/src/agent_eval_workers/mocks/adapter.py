"""Deterministic mock Adapter — streams NDM events and artifacts continuously."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.normalized_model import (
    MessageAction,
    NormalizedAction,
    ToolCallAction,
)

from agent_eval_workers.event_pipeline.models import (
    IncomingArtifact,
    IncomingExecutionEvent,
)
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.mocks.stream import EventStreamPort

AdapterHook = Callable[[RunId], None]


def default_action_script() -> tuple[NormalizedAction, ...]:
    return (
        MessageAction(role="user", content_summary="solve the case"),
        ToolCallAction(tool_name="read_file", arguments={"path": "main.py"}),
        MessageAction(role="assistant", content_summary="done"),
    )


@dataclass
class MockAdapter:
    """Platform-shaped Adapter mock: initialize → stream → finish."""

    stream: EventStreamPort
    actions: tuple[NormalizedAction, ...] = field(default_factory=default_action_script)
    emit_artifact: bool = True
    fail_on_run: bool = False
    after_start: AdapterHook | None = None
    before_run: AdapterHook | None = None
    after_run: AdapterHook | None = None
    started: list[RunId] = field(default_factory=list)
    ran: list[RunId] = field(default_factory=list)
    finished: list[RunId] = field(default_factory=list)
    emitted_event_ids: list[str] = field(default_factory=list)

    def start(self, run_id: RunId) -> None:
        self.started.append(run_id)
        if self.after_start is not None:
            self.after_start(run_id)

    def run(self, run_id: RunId) -> None:
        """Stream events continuously as they are 'observed' — no end buffering."""
        if self.before_run is not None:
            self.before_run(run_id)
        if self.fail_on_run:
            raise RecoverableExecutionError(
                f"Mock adapter failed for {run_id.value}",
                cause=FailureCause.ADAPTER_FAILURE,
            )
        self.ran.append(run_id)
        artifact_ids: tuple[str, ...] = ()
        if self.emit_artifact:
            artifact_id = f"{run_id.value}-art-0"
            self.stream.submit_artifact(
                IncomingArtifact(
                    run_id=run_id,
                    artifact_id=artifact_id,
                    kind="diff",
                    storage_key=f"mock://{run_id.value}/diff",
                    content_type="text/plain",
                    size_bytes=42,
                    checksum=f"sha256:{run_id.value}",
                )
            )
            artifact_ids = (artifact_id,)

        for index, action in enumerate(self.actions):
            event_id = f"{run_id.value}-evt-{index}"
            refs = artifact_ids if index == len(self.actions) - 1 else ()
            self.stream.submit_event(
                IncomingExecutionEvent(
                    run_id=run_id,
                    execution_event_id=event_id,
                    action=action,
                    artifact_ids=refs,
                )
            )
            self.emitted_event_ids.append(event_id)
        if self.after_run is not None:
            self.after_run(run_id)

    def finish(self, run_id: RunId) -> None:
        self.finished.append(run_id)
