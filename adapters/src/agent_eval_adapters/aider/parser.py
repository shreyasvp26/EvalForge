"""Aider NDJSON stream parser → NativeObservation."""

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
            f"Invalid Aider JSON line: {exc}",
            details={"line": line[:500]},
            cause=exc,
        ) from exc

    if not isinstance(payload, dict):
        raise MalformedOutputError(
            "Aider stream line must be a JSON object",
            details={"line": line[:500]},
        )

    event_type = str(payload.get("type") or payload.get("event") or "").strip()
    if not event_type:
        raise MalformedOutputError(
            "Aider stream object missing type",
            details={"line": line[:500]},
        )

    event_type = event_type.lower()
    if event_type == "message":
        return _parse_message(payload, stamp, raw=line)
    if event_type in {"edit", "file_edit"}:
        return _parse_file_edit(payload, stamp, raw=line)
    if event_type in {"shell", "run"}:
        return _parse_shell(payload, stamp, raw=line)
    if event_type == "tool_call":
        return _parse_tool_call(payload, stamp, raw=line)
    if event_type in {"stdout", "stderr"}:
        kind = (
            ObservationKind.STDERR if event_type == "stderr" else ObservationKind.STDOUT
        )
        return [
            observation_now(
                kind,
                payload={"content": str(payload.get("content", ""))},
                raw=line,
                timestamp=stamp,
            )
        ]
    if event_type == "commit":
        message = str(payload.get("message") or payload.get("content") or "")
        return [
            observation_now(
                ObservationKind.MESSAGE,
                payload={"role": "system", "content": f"commit: {message}"},
                raw=line,
                timestamp=stamp,
            )
        ]
    if event_type in {"complete", "done", "result"}:
        return _parse_completion(payload, stamp, raw=line)
    if event_type == "error":
        return [
            observation_now(
                ObservationKind.ERROR,
                payload={
                    "message": str(
                        payload.get("message") or payload.get("error") or "error"
                    ),
                },
                raw=line,
                timestamp=stamp,
            )
        ]
    return [
        observation_now(
            ObservationKind.MESSAGE,
            payload={"role": "system", "content": f"untyped:{event_type}"},
            raw=line,
            timestamp=stamp,
        )
    ]


def _parse_message(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content", "")
        role = str(message.get("role") or "assistant")
    else:
        content = payload.get("content") or payload.get("text") or ""
        role = str(payload.get("role") or "assistant")
    return [
        observation_now(
            ObservationKind.MESSAGE,
            payload={"role": role, "content": str(content)},
            raw=raw,
            timestamp=stamp,
        )
    ]


def _parse_tool_call(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    name = str(
        payload.get("name")
        or payload.get("tool_name")
        or payload.get("tool")
        or "unknown"
    ).strip()
    arguments = (
        payload.get("arguments") or payload.get("args") or payload.get("input") or {}
    )
    if not isinstance(arguments, dict):
        arguments = {"value": arguments}

    observations: list[NativeObservation] = [
        observation_now(
            ObservationKind.TOOL_INVOCATION,
            payload={
                "tool_name": name or "unknown",
                "arguments": dict(arguments),
                "tool_use_id": str(payload.get("id") or payload.get("call_id") or ""),
            },
            raw=raw,
            timestamp=stamp,
        )
    ]

    lowered = name.lower().replace("-", "_")
    if lowered in {"edit", "write", "write_file", "edit_file"}:
        path = str(
            arguments.get("path")
            or arguments.get("file_path")
            or arguments.get("filePath")
            or ""
        )
        diff = str(
            arguments.get("diff")
            or arguments.get("content")
            or arguments.get("new_string")
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
    if lowered in {"shell", "bash", "run"}:
        command = str(arguments.get("command") or arguments.get("cmd") or "")
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


def _parse_file_edit(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    path = str(
        payload.get("path") or payload.get("file_path") or payload.get("filePath") or ""
    )
    diff = str(
        payload.get("diff")
        or payload.get("content")
        or payload.get("diff_summary")
        or ""
    )
    if not path:
        raise MalformedOutputError(
            "Aider file edit missing path",
            details={"line": raw[:500]},
        )
    return [
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
    ]


def _parse_shell(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    command = str(payload.get("command") or payload.get("cmd") or "").strip()
    if not command:
        raise MalformedOutputError(
            "Aider shell event missing command",
            details={"line": raw[:500]},
        )
    exit_code = payload.get("exit_code")
    return [
        observation_now(
            ObservationKind.SHELL_COMMAND,
            payload={
                "command": command,
                "exit_code": int(exit_code) if exit_code is not None else None,
            },
            raw=raw,
            timestamp=stamp,
        )
    ]


def _parse_completion(
    payload: Mapping[str, Any],
    stamp: datetime,
    *,
    raw: str,
) -> list[NativeObservation]:
    status = str(payload.get("status") or payload.get("subtype") or "completed").lower()
    is_error = bool(payload.get("is_error", False)) or status in {
        "error",
        "failure",
        "failed",
        "agent_failed",
    }
    if is_error:
        return [
            observation_now(
                ObservationKind.ERROR,
                payload={
                    "message": str(
                        payload.get("message")
                        or payload.get("result")
                        or payload.get("error")
                        or status
                    ),
                },
                raw=raw,
                timestamp=stamp,
            ),
            observation_now(
                ObservationKind.COMPLETION,
                payload={"status": "agent_failed", "subtype": status},
                raw=raw,
                timestamp=stamp,
            ),
        ]
    return [
        observation_now(
            ObservationKind.COMPLETION,
            payload={
                "status": "completed",
                "subtype": status,
                "result": str(payload.get("result", "")),
            },
            raw=raw,
            timestamp=stamp,
        )
    ]
