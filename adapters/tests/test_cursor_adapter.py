"""Cursor Adapter integration tests — mocked stream sources only."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

import pytest
from adapter_fakes import (
    FlagCancellation,
    MockSandboxExec,
    RecordingSink,
    make_handle,
)
from agent_eval_adapters.cursor import CursorAdapter
from agent_eval_adapters.cursor.parser import parse_stream_line
from agent_eval_adapters.sdk import (
    AdapterInitializationError,
    AdapterOutcome,
    DefaultTranslator,
    EventEmitter,
    ExecutionConfig,
    ExecutionContext,
    MalformedOutputError,
    ObservationKind,
    run_adapter,
)
from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_adapters.sdk.translator import observation_now
from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    MessageAction,
    OutputAction,
    ShellCommandAction,
    ToolCallAction,
)


def _context(
    *,
    sandbox_exec: MockSandboxExec | None = None,
    cancellation: FlagCancellation | None = None,
    timeout_seconds: float = 30.0,
    prompt: str = "fix the bug",
    artifact_inline_max_bytes: int = 8_192,
) -> ExecutionContext:
    return ExecutionContext(
        working_directory="/workspace",
        sandbox=make_handle(),
        sandbox_exec=sandbox_exec or MockSandboxExec(),
        environment={"CURSOR_API_KEY": "test"},
        run=RunMetadata(
            run_id="run-cursor-1",
            agent_version_id="agent-v1",
            adapter_version_id="adapter-cursor-v1",
            prompt_version_id="prompt-v1",
            case_version_id="case-v1",
        ),
        correlation_id="corr-cursor",
        config=ExecutionConfig(
            timeout_seconds=timeout_seconds,
            artifact_inline_max_bytes=artifact_inline_max_bytes,
        ),
        prompt=prompt,
        cancellation=cancellation,
    )


SAMPLE_STREAM = [
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "Inspecting main.py",
            },
        }
    ),
    json.dumps(
        {
            "type": "tool_call",
            "id": "call_1",
            "name": "read_file",
            "arguments": {"path": "main.py"},
        }
    ),
    json.dumps(
        {
            "type": "tool_call",
            "id": "call_2",
            "name": "edit_file",
            "arguments": {
                "path": "main.py",
                "old_string": "a",
                "new_string": "b",
            },
        }
    ),
    json.dumps(
        {
            "type": "shell",
            "command": "pytest -q",
            "exit_code": 0,
        }
    ),
    json.dumps(
        {
            "type": "tool_result",
            "name": "shell",
            "id": "call_3",
            "result": "1 passed",
        }
    ),
    json.dumps({"type": "stdout", "content": "tests ok"}),
    json.dumps({"type": "done", "status": "success", "result": "fixed"}),
]


def test_cursor_happy_path_streaming_and_translation() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield from SAMPLE_STREAM

    sink = RecordingSink()
    result = run_adapter(CursorAdapter(stream_source=source), _context(), sink)
    assert result.outcome is AdapterOutcome.COMPLETED
    assert result.events_emitted >= 5
    kinds = [type(e.action) for e in sink.events]
    assert MessageAction in kinds
    assert ToolCallAction in kinds
    assert FileEditAction in kinds
    assert ShellCommandAction in kinds
    assert OutputAction in kinds


def test_cursor_event_ordering_and_exactly_once() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield from SAMPLE_STREAM

    sink = RecordingSink()
    result = run_adapter(CursorAdapter(stream_source=source), _context(), sink)
    sink_ids = [e.event_id for e in sink.events]
    assert sink_ids == list(dict.fromkeys(sink_ids))
    event_markers = [m for m in result.emission_order if m.startswith("event:")]
    assert event_markers == [f"event:{eid}" for eid in sink_ids]

    emitter = EventEmitter(sink=RecordingSink())
    obs = observation_now(
        ObservationKind.MESSAGE,
        payload={"role": "assistant", "content": "hi"},
    )
    events = DefaultTranslator().translate(obs, _context())
    assert emitter.emit_event(events[0]) is True
    assert emitter.emit_event(events[0]) is False


def test_cursor_cancellation_during_stream() -> None:
    cancel = FlagCancellation()

    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield SAMPLE_STREAM[0]
        cancel.cancelled = True
        yield SAMPLE_STREAM[1]

    result = run_adapter(
        CursorAdapter(stream_source=source),
        _context(cancellation=cancel),
        RecordingSink(),
    )
    assert result.outcome is AdapterOutcome.CANCELLED


def test_cursor_timeout_during_stream() -> None:
    def slow_source(_ctx: ExecutionContext) -> Iterator[str]:
        yield SAMPLE_STREAM[0]
        time.sleep(0.05)
        yield SAMPLE_STREAM[-1]

    result = run_adapter(
        CursorAdapter(stream_source=slow_source),
        _context(timeout_seconds=0.01),
        RecordingSink(),
    )
    assert result.outcome is AdapterOutcome.TIMED_OUT


def test_cursor_malformed_output_recovery() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield "not-json{{{"
        yield SAMPLE_STREAM[-1]

    sink = RecordingSink()
    result = run_adapter(CursorAdapter(stream_source=source), _context(), sink)
    assert result.outcome is AdapterOutcome.COMPLETED
    assert any("malformed" in str(e.action.content_summary) for e in sink.events)


def test_cursor_agent_failed_completion() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield json.dumps(
            {"type": "done", "status": "failed", "message": "could not solve"}
        )

    result = run_adapter(
        CursorAdapter(stream_source=source),
        _context(),
        RecordingSink(),
    )
    assert result.outcome is AdapterOutcome.AGENT_FAILED


def test_cursor_large_output_emits_artifact() -> None:
    big = "x" * 10_000

    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield json.dumps(
            {
                "type": "file_edit",
                "path": "big.txt",
                "content": big,
            }
        )
        yield json.dumps({"type": "done", "status": "success"})

    sink = RecordingSink()
    result = run_adapter(
        CursorAdapter(stream_source=source),
        _context(artifact_inline_max_bytes=100),
        sink,
    )
    assert result.outcome is AdapterOutcome.COMPLETED
    assert result.artifacts_emitted >= 1
    assert sink.artifacts


def test_cursor_sandbox_process_startup_path() -> None:
    stdout = "\n".join(SAMPLE_STREAM)
    exec_port = MockSandboxExec(stdout=stdout)
    result = run_adapter(
        CursorAdapter(),
        _context(sandbox_exec=exec_port),
        RecordingSink(),
    )
    assert result.outcome is AdapterOutcome.COMPLETED
    assert exec_port.commands[0][0] == "agent"
    assert "--output-format" in exec_port.commands[0]


def test_cursor_initialize_requires_prompt() -> None:
    with pytest.raises(AdapterInitializationError):
        run_adapter(CursorAdapter(), _context(prompt=""), RecordingSink())


def test_cursor_parser_rejects_non_object() -> None:
    with pytest.raises(MalformedOutputError):
        parse_stream_line("[1,2,3]")
