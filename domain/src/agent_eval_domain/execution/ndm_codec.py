"""Serialize / deserialize Normalized Domain Model actions (payload form).

Shared by Application (commands) and Infrastructure (ORM JSON columns).
"""

from __future__ import annotations

from typing import Any

from agent_eval_domain.execution.normalized_model import (
    ActionKind,
    FileEditAction,
    MessageAction,
    NormalizedAction,
    OutputAction,
    ShellCommandAction,
    ToolCallAction,
    action_kind_of,
)


def action_to_payload(action: NormalizedAction) -> dict[str, Any]:
    kind = action_kind_of(action).value
    if isinstance(action, ToolCallAction):
        return {
            "kind": kind,
            "tool_name": action.tool_name,
            "arguments": dict(action.arguments),
            "result_summary": action.result_summary,
        }
    if isinstance(action, FileEditAction):
        return {
            "kind": kind,
            "path": action.path,
            "diff_summary": action.diff_summary,
            "language": action.language,
        }
    if isinstance(action, ShellCommandAction):
        return {
            "kind": kind,
            "command": action.command,
            "exit_code": action.exit_code,
            "cwd": action.cwd,
        }
    if isinstance(action, OutputAction):
        return {
            "kind": kind,
            "stream": action.stream,
            "content_summary": action.content_summary,
        }
    if isinstance(action, MessageAction):
        return {
            "kind": kind,
            "role": action.role,
            "content_summary": action.content_summary,
        }
    msg = f"Unsupported action type: {type(action)!r}"
    raise TypeError(msg)


def action_from_payload(payload: dict[str, Any]) -> NormalizedAction:
    kind = ActionKind(str(payload["kind"]))
    if kind is ActionKind.TOOL_CALL:
        return ToolCallAction(
            tool_name=str(payload["tool_name"]),
            arguments=dict(payload.get("arguments") or {}),
            result_summary=payload.get("result_summary"),
        )
    if kind is ActionKind.FILE_EDIT:
        return FileEditAction(
            path=str(payload["path"]),
            diff_summary=str(payload["diff_summary"]),
            language=payload.get("language"),
        )
    if kind is ActionKind.SHELL_COMMAND:
        return ShellCommandAction(
            command=str(payload["command"]),
            exit_code=payload.get("exit_code"),
            cwd=payload.get("cwd"),
        )
    if kind is ActionKind.OUTPUT:
        return OutputAction(
            stream=str(payload["stream"]),
            content_summary=str(payload["content_summary"]),
        )
    if kind is ActionKind.MESSAGE:
        return MessageAction(
            role=str(payload["role"]),
            content_summary=str(payload["content_summary"]),
        )
    msg = f"Unsupported action kind: {kind}"
    raise ValueError(msg)
