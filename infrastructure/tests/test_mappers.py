"""Mapper unit tests for NDM action payload round-trips."""

from __future__ import annotations

from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    MessageAction,
    OutputAction,
    ShellCommandAction,
    ToolCallAction,
)
from agent_eval_infrastructure.mappers.ndm import action_from_payload, action_to_payload


def test_ndm_action_roundtrips() -> None:
    actions = [
        ToolCallAction(tool_name="read", arguments={"p": "1"}, result_summary="ok"),
        FileEditAction(path="a.py", diff_summary="+x", language="python"),
        ShellCommandAction(command="ls", exit_code=0, cwd="/tmp"),
        OutputAction(stream="stdout", content_summary="hi"),
        MessageAction(role="assistant", content_summary="done"),
    ]
    for action in actions:
        restored = action_from_payload(action_to_payload(action))
        assert restored == action
