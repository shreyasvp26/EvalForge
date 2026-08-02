"""Test doubles for Grader integration tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from agent_eval_domain.common.ids import ExecutionEventId, RunId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent
from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    NormalizedAction,
    OutputAction,
    ShellCommandAction,
    action_kind_of,
)
from agent_eval_graders.sdk.models import GradingRunMetadata, ProducedScore
from agent_eval_graders.sdk.ports import RunReader, ScoreSink


@dataclass
class InMemoryRunReader:
    """RunReader backed by in-memory events/artifacts — no repositories."""

    run_id: str = "run-1"
    _events: list[ExecutionEvent] = field(default_factory=list)
    _artifacts: list[Artifact] = field(default_factory=list)

    def metadata(self) -> GradingRunMetadata:
        return GradingRunMetadata(
            run_id=RunId(self.run_id),
            agent_version_id="agent-v1",
            adapter_version_id="adapter-v1",
            case_version_id="case-v1",
            prompt_version_id="prompt-v1",
            status="grading",
        )

    def events(self) -> Sequence[ExecutionEvent]:
        return tuple(self._events)

    def artifacts(self) -> Sequence[Artifact]:
        return tuple(self._artifacts)

    def add_shell(self, command: str, exit_code: int | None) -> None:
        self._add(ShellCommandAction(command=command, exit_code=exit_code))

    def add_edit(self, path: str, diff: str = "@@ -1 +1 @@\n-a\n+b\n") -> None:
        self._add(FileEditAction(path=path, diff_summary=diff))

    def add_output(self, content: str, stream: str = "stdout") -> None:
        self._add(OutputAction(stream=stream, content_summary=content))

    def _add(self, action: NormalizedAction) -> None:
        seq = len(self._events)
        self._events.append(
            ExecutionEvent(
                id=ExecutionEventId(f"evt-{seq}"),
                run_id=RunId(self.run_id),
                sequence=seq,
                kind=action_kind_of(action),
                action=action,
                occurred_at=datetime.now(UTC),
            )
        )


@dataclass
class CollectingSink:
    scores: list[ProducedScore] = field(default_factory=list)
    failures: list[tuple[str, str, str]] = field(default_factory=list)

    def on_score(self, produced: ProducedScore) -> None:
        self.scores.append(produced)

    def on_failure(
        self,
        *,
        grader_id: str,
        grader_version_id: str,
        message: str,
    ) -> None:
        self.failures.append((grader_id, grader_version_id, message))


def assert_is_run_reader(reader: InMemoryRunReader) -> RunReader:
    return reader


def assert_is_sink(sink: CollectingSink) -> ScoreSink:
    return sink
