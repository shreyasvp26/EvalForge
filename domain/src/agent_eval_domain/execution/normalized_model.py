"""Normalized Domain Model — agent-agnostic action shapes (Domain Model §1).

Adapters produce these; Execution Engine and Graders consume them.
No vendor-specific fields are permitted here (Invariant 8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agent_eval_domain.common.errors import InvariantViolation


class ActionKind(StrEnum):
    TOOL_CALL = "tool_call"
    FILE_EDIT = "file_edit"
    SHELL_COMMAND = "shell_command"
    OUTPUT = "output"
    MESSAGE = "message"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ToolCallAction:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result_summary: str | None = None

    def __post_init__(self) -> None:
        if not self.tool_name.strip():
            raise InvariantViolation(
                "Tool call name must be non-empty",
                code="INVALID_TOOL_CALL",
            )


@dataclass(frozen=True, slots=True)
class FileEditAction:
    path: str
    diff_summary: str
    language: str | None = None

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise InvariantViolation(
                "File edit path must be non-empty",
                code="INVALID_FILE_EDIT",
            )


@dataclass(frozen=True, slots=True)
class ShellCommandAction:
    command: str
    exit_code: int | None = None
    cwd: str | None = None

    def __post_init__(self) -> None:
        if not self.command.strip():
            raise InvariantViolation(
                "Shell command must be non-empty",
                code="INVALID_SHELL_COMMAND",
            )


@dataclass(frozen=True, slots=True)
class OutputAction:
    stream: str
    content_summary: str

    def __post_init__(self) -> None:
        if not self.stream.strip():
            raise InvariantViolation(
                "Output stream must be non-empty",
                code="INVALID_OUTPUT",
            )


@dataclass(frozen=True, slots=True)
class MessageAction:
    role: str
    content_summary: str

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise InvariantViolation(
                "Message role must be non-empty",
                code="INVALID_MESSAGE",
            )


NormalizedAction = (
    ToolCallAction | FileEditAction | ShellCommandAction | OutputAction | MessageAction
)


def action_kind_of(action: NormalizedAction) -> ActionKind:
    if isinstance(action, ToolCallAction):
        return ActionKind.TOOL_CALL
    if isinstance(action, FileEditAction):
        return ActionKind.FILE_EDIT
    if isinstance(action, ShellCommandAction):
        return ActionKind.SHELL_COMMAND
    if isinstance(action, OutputAction):
        return ActionKind.OUTPUT
    if isinstance(action, MessageAction):
        return ActionKind.MESSAGE
    raise InvariantViolation(
        f"Unknown normalized action type: {type(action)!r}",
        code="UNKNOWN_ACTION_KIND",
    )
