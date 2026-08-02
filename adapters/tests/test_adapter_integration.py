"""Adapter SDK + Claude Code integration tests (mocked Sandbox only)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from adapter_fakes import (
    FlagCancellation,
    MockSandboxExec,
    RecordingSink,
    make_handle,
)
from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.claude_code.parser import parse_stream_line
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
        environment={"ANTHROPIC_API_KEY": "test"},
        run=RunMetadata(
            run_id="run-1",
            agent_version_id="agent-v1",
            adapter_version_id="adapter-v1",
            prompt_version_id="prompt-v1",
            case_version_id="case-v1",
        ),
        correlation_id="corr-1",
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
                "content": [
                    {"type": "text", "text": "I will inspect the file"},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "Read",
                        "input": {"file_path": "main.py"},
                    },
                ],
            },
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_2",
                        "name": "Edit",
                        "input": {
                            "file_path": "main.py",
                            "old_string": "a",
                            "new_string": "b",
                        },
                    }
                ]
            },
        }
    ),
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_3",
                        "name": "Bash",
                        "input": {"command": "pytest -q"},
                    }
                ]
            },
        }
    ),
    json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_3",
                        "content": "1 passed",
                    }
                ]
            },
        }
    ),
    json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "done",
        }
    ),
]


def test_lifecycle_happy_path_streaming_and_translation() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield from SAMPLE_STREAM

    sink = RecordingSink()
    adapter = ClaudeCodeAdapter(stream_source=source)
    result = run_adapter(adapter, _context(), sink)

    assert result.outcome is AdapterOutcome.COMPLETED
    assert result.events_emitted >= 5
    kinds = [type(e.action) for e in sink.events]
    assert MessageAction in kinds
    assert ToolCallAction in kinds
    assert FileEditAction in kinds
    assert ShellCommandAction in kinds
    assert OutputAction in kinds
    # Ordered emission: first event precedes last
    assert sink.events[0].observed_at <= sink.events[-1].observed_at
    assert any(p.message.startswith("tool:") for p in sink.progress)


def test_event_ordering_matches_stream_order() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield from SAMPLE_STREAM

    sink = RecordingSink()
    result = run_adapter(ClaudeCodeAdapter(stream_source=source), _context(), sink)
    assert sink.events
    # Sink order is the emission order for events.
    sink_ids = [e.event_id for e in sink.events]
    assert sink_ids == list(dict.fromkeys(sink_ids))  # unique, order-preserving
    event_markers = [m for m in result.emission_order if m.startswith("event:")]
    assert event_markers == [f"event:{eid}" for eid in sink_ids]


def test_exactly_once_emission() -> None:
    sink = RecordingSink()
    emitter = EventEmitter(sink=sink)
    obs = observation_now(
        ObservationKind.MESSAGE,
        payload={"role": "assistant", "content": "hi"},
    )
    events = DefaultTranslator().translate(obs, _context())
    assert len(events) == 1
    assert emitter.emit_event(events[0]) is True
    assert emitter.emit_event(events[0]) is False
    assert len(sink.events) == 1


def test_cancellation_during_stream() -> None:
    cancel = FlagCancellation()

    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield SAMPLE_STREAM[0]
        cancel.cancelled = True
        yield SAMPLE_STREAM[1]

    sink = RecordingSink()
    result = run_adapter(
        ClaudeCodeAdapter(stream_source=source),
        _context(cancellation=cancel),
        sink,
    )
    assert result.outcome is AdapterOutcome.CANCELLED
    assert sink.errors


def test_timeout_during_stream() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield SAMPLE_STREAM[0]
        # Simulate long gap by raising via adapter timeout on next check:
        # zero timeout forces timeout on second line after start.
        yield SAMPLE_STREAM[1]

    sink = RecordingSink()
    # Use extremely small timeout and slow source
    import time

    def slow_source(_ctx: ExecutionContext) -> Iterator[str]:
        yield SAMPLE_STREAM[0]
        time.sleep(0.05)
        yield SAMPLE_STREAM[-1]

    result = run_adapter(
        ClaudeCodeAdapter(stream_source=slow_source),
        _context(timeout_seconds=0.01),
        sink,
    )
    assert result.outcome is AdapterOutcome.TIMED_OUT


def test_malformed_output_recovery() -> None:
    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield "not-json{{{"
        yield SAMPLE_STREAM[-1]

    sink = RecordingSink()
    result = run_adapter(ClaudeCodeAdapter(stream_source=source), _context(), sink)
    assert result.outcome is AdapterOutcome.COMPLETED
    assert any(isinstance(e.action, MessageAction) for e in sink.events)
    # Malformed line became ERROR observation → MessageAction system
    assert any("malformed" in str(e.action.content_summary) for e in sink.events)


def test_agent_failed_completion() -> None:
    lines = [
        json.dumps(
            {
                "type": "result",
                "subtype": "error",
                "is_error": True,
                "result": "could not solve",
            }
        )
    ]

    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield from lines

    sink = RecordingSink()
    result = run_adapter(ClaudeCodeAdapter(stream_source=source), _context(), sink)
    assert result.outcome is AdapterOutcome.AGENT_FAILED


def test_initialize_requires_prompt_without_stream_source() -> None:
    sink = RecordingSink()
    with pytest.raises(AdapterInitializationError):
        run_adapter(
            ClaudeCodeAdapter(),
            _context(prompt=""),
            sink,
        )


def test_sandbox_process_startup_path() -> None:
    stdout = "\n".join(SAMPLE_STREAM)
    exec_port = MockSandboxExec(stdout=stdout)
    sink = RecordingSink()
    result = run_adapter(ClaudeCodeAdapter(), _context(sandbox_exec=exec_port), sink)
    assert result.outcome is AdapterOutcome.COMPLETED
    assert exec_port.commands
    assert exec_port.commands[0][0] == "claude"
    assert "--output-format" in exec_port.commands[0]


def test_large_payload_emits_artifact() -> None:
    big = "x" * 10_000
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Write",
                        "input": {"file_path": "big.txt", "content": big},
                    }
                ]
            },
        }
    )
    line2 = json.dumps(
        {"type": "result", "subtype": "success", "is_error": False, "result": "ok"}
    )

    def source(_ctx: ExecutionContext) -> Iterator[str]:
        yield line
        yield line2

    sink = RecordingSink()
    result = run_adapter(
        ClaudeCodeAdapter(stream_source=source),
        _context(artifact_inline_max_bytes=100),
        sink,
    )
    assert result.outcome is AdapterOutcome.COMPLETED
    assert result.artifacts_emitted >= 1
    assert sink.artifacts


def test_parser_rejects_non_object() -> None:
    with pytest.raises(MalformedOutputError):
        parse_stream_line("[1,2,3]")


def test_context_environment_is_immutable() -> None:
    ctx = _context()
    with pytest.raises(TypeError):
        ctx.environment["X"] = "y"  # type: ignore[index]


def test_translator_tool_and_shell() -> None:
    translator = DefaultTranslator()
    ctx = _context()
    tool = observation_now(
        ObservationKind.TOOL_INVOCATION,
        payload={"tool_name": "Read", "arguments": {"path": "a.py"}},
    )
    events = translator.translate(tool, ctx)
    assert isinstance(events[0].action, ToolCallAction)

    shell = observation_now(
        ObservationKind.SHELL_COMMAND,
        payload={"command": "ls", "exit_code": 0},
    )
    events = translator.translate(shell, ctx)
    assert isinstance(events[0].action, ShellCommandAction)
