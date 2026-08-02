"""Helpers for objective graders — pattern matching on recorded events only."""

from __future__ import annotations

import re
from collections.abc import Sequence

from agent_eval_domain.execution.entities import ExecutionEvent
from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    OutputAction,
    ShellCommandAction,
)


def shell_events(events: Sequence[ExecutionEvent]) -> list[ShellCommandAction]:
    return [e.action for e in events if isinstance(e.action, ShellCommandAction)]


def file_edit_events(events: Sequence[ExecutionEvent]) -> list[FileEditAction]:
    return [e.action for e in events if isinstance(e.action, FileEditAction)]


def output_events(events: Sequence[ExecutionEvent]) -> list[OutputAction]:
    return [e.action for e in events if isinstance(e.action, OutputAction)]


def matching_shell(
    events: Sequence[ExecutionEvent],
    patterns: Sequence[str],
) -> list[ShellCommandAction]:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    matches: list[ShellCommandAction] = []
    for action in shell_events(events):
        if any(rx.search(action.command) for rx in compiled):
            matches.append(action)
    return matches


def last_exit_code(actions: Sequence[ShellCommandAction]) -> int | None:
    for action in reversed(actions):
        if action.exit_code is not None:
            return action.exit_code
    return None


def all_passed(actions: Sequence[ShellCommandAction]) -> bool:
    if not actions:
        return False
    return all(a.exit_code == 0 for a in actions if a.exit_code is not None) and any(
        a.exit_code is not None for a in actions
    )
