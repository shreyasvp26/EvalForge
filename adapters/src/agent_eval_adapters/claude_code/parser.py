"""Claude Code stream-json / NDJSON parser → NativeObservation."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from typing import Any

from agent_eval_adapters.sdk.exceptions import MalformedOutputError
from agent_eval_adapters.sdk.models import NativeObservation, ObservationKind
from agent_eval_adapters.sdk.translator import observation_now


def parse_stream_lines(
    lines: Iterator[str] | list[str],
    *,
    now: datetime | None = None,
) -> Iterator[NativeObservation]:
    """Parse Claude Code NDJSON stream lines into native observations."""
    for line in lines:
        text = line.strip()
        if not text:
            continue
        yield from parse_stream_line(text, now=now)


def parse_stream_line(
    line: str,
    *,
    now: datetime | None = None,
) -> list[NativeObservation]:
    stamp = now or datetime.now(UTC)
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise MalformedOutputError(
            f"Invalid Claude Code JSON line: {exc}",
            details={"line": line[:500]},
            cause=exc,
        ) from exc

    if not isinstance(payload, dict):
        raise MalformedOutputError(
            "Claude Code stream line must be a JSON object",
            details={"line": line[:500]},
        )

    event_type = str(payload.get("type", "")).strip()
    if not event_type:
        raise MalformedOutputError(
            "Claude Code stream object missing type",
            details={"line": line[:500]},
        )

    if event_type == "assistant":
        return _parse_assistant(payload, stamp, raw=line)
    if event_type == "user":
        return _parse_user(payload, stamp, raw=line)
    if event_type == "result":
        return _parse_result(payload, stamp, raw=line)
    if event_type in {"system", "progress"}:
        return [
            observation_now(
                ObservationKind.MESSAGE,
                payload={
                    "role": "system",
                    "content": str(payload.get("subtype", event_type)),
                },
                raw=line,
                timestamp=stamp,
            )
        ]
    if event_type == "error":
        return [
            observation_now(
                ObservationKind.ERROR,
                payload={
                    "message": str(
                        payload.get("error", payload.get("message", "error"))
                    ),
                },
                raw=line,
                timestamp=stamp,
            )
        ]
    # Unknown types — surface as message so completeness is preserved.
    return [
        observation_now(
            ObservationKind.MESSAGE,
            payload={"role": "system", "content": f"untyped:{event_type}"},
            raw=line,
            timestamp=stamp,
        )
    ]


def _parse_assistant(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    observations: list[NativeObservation] = []
    message = payload.get("message")
    if not isinstance(message, dict):
        return [
            observation_now(
                ObservationKind.MESSAGE,
                payload={"role": "assistant", "content": ""},
                raw=raw,
                timestamp=stamp,
            )
        ]
    content = message.get("content", [])
    if isinstance(content, str):
        observations.append(
            observation_now(
                ObservationKind.MESSAGE,
                payload={"role": "assistant", "content": content},
                raw=raw,
                timestamp=stamp,
            )
        )
        return observations
    if not isinstance(content, list):
        return observations

    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type", ""))
        if block_type == "text":
            observations.append(
                observation_now(
                    ObservationKind.MESSAGE,
                    payload={
                        "role": "assistant",
                        "content": str(block.get("text", "")),
                    },
                    raw=raw,
                    timestamp=stamp,
                )
            )
        elif block_type == "tool_use":
            observations.extend(_parse_tool_use(block, stamp, raw=raw))
    return observations


def _parse_tool_use(
    block: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    name = str(block.get("name", "")).strip()
    tool_input = block.get("input", {})
    if not isinstance(tool_input, dict):
        tool_input = {"value": tool_input}

    observations: list[NativeObservation] = [
        observation_now(
            ObservationKind.TOOL_INVOCATION,
            payload={
                "tool_name": name or "unknown",
                "arguments": dict(tool_input),
                "tool_use_id": str(block.get("id", "")),
            },
            raw=raw,
            timestamp=stamp,
        )
    ]

    # File-change detection for Edit / Write / NotebookEdit style tools.
    lowered = name.lower()
    if lowered in {"edit", "write", "notebookedit", "multiedit"}:
        path = str(
            tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("filePath")
            or ""
        )
        diff = str(
            tool_input.get("new_string")
            or tool_input.get("content")
            or tool_input.get("old_string")
            or ""
        )
        if path:
            observations.append(
                observation_now(
                    ObservationKind.FILE_CHANGE,
                    payload={
                        "path": path,
                        "diff_summary": diff[:2000],
                        "content": diff,
                    },
                    raw=raw,
                    timestamp=stamp,
                )
            )

    if lowered in {"bash", "shell", "bashoutput"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if command:
            observations.append(
                observation_now(
                    ObservationKind.SHELL_COMMAND,
                    payload={"command": command},
                    raw=raw,
                    timestamp=stamp,
                )
            )
    return observations


def _parse_user(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    observations: list[NativeObservation] = []
    message = payload.get("message")
    if not isinstance(message, dict):
        return observations
    content = message.get("content", [])
    if not isinstance(content, list):
        return observations
    for block in content:
        if not isinstance(block, dict):
            continue
        if str(block.get("type", "")) != "tool_result":
            continue
        result = block.get("content", "")
        if isinstance(result, list):
            result = json.dumps(result)
        observations.append(
            observation_now(
                ObservationKind.TOOL_INVOCATION,
                payload={
                    "tool_name": "tool_result",
                    "arguments": {"tool_use_id": block.get("tool_use_id")},
                    "result_summary": str(result)[:2000],
                },
                raw=raw,
                timestamp=stamp,
            )
        )
        # Surface large tool results as stdout-ish content for completeness.
        text = str(result)
        if text:
            observations.append(
                observation_now(
                    ObservationKind.STDOUT,
                    payload={"content": text},
                    raw=raw,
                    timestamp=stamp,
                )
            )
    return observations


def _parse_result(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    is_error = bool(payload.get("is_error", False))
    subtype = str(payload.get("subtype", "success"))
    if is_error or subtype in {"error", "failure"}:
        return [
            observation_now(
                ObservationKind.ERROR,
                payload={
                    "message": str(
                        payload.get("result", payload.get("error", subtype))
                    ),
                },
                raw=raw,
                timestamp=stamp,
            ),
            observation_now(
                ObservationKind.COMPLETION,
                payload={"status": "agent_failed", "subtype": subtype},
                raw=raw,
                timestamp=stamp,
            ),
        ]
    return [
        observation_now(
            ObservationKind.COMPLETION,
            payload={
                "status": "completed",
                "subtype": subtype,
                "result": str(payload.get("result", "")),
            },
            raw=raw,
            timestamp=stamp,
        )
    ]
