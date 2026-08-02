"""Declared adapter capabilities (informational for callers / tests)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterCapabilities:
    """What a given Adapter Version can observe / emit."""

    streams_stdout: bool = True
    streams_stderr: bool = True
    observes_tool_calls: bool = True
    observes_file_changes: bool = True
    observes_shell_commands: bool = True
    supports_cancellation: bool = True
    supports_timeout: bool = True
