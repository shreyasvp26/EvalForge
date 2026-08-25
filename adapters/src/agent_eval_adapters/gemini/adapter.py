"""Gemini CLI production Adapter — translation only."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from agent_eval_sandbox.models import ExecutionRequest

from agent_eval_adapters.gemini.parser import parse_stream_line
from agent_eval_adapters.sdk.adapter import BaseAdapter
from agent_eval_adapters.sdk.capabilities import AdapterCapabilities
from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.exceptions import (
    AdapterCancellationError,
    AdapterInitializationError,
    AdapterTimeoutError,
    MalformedOutputError,
)
from agent_eval_adapters.sdk.models import (
    AdapterOutcome,
    NativeObservation,
    ObservationKind,
)
from agent_eval_adapters.sdk.translator import observation_now

StreamSource = Callable[[ExecutionContext], Iterator[str]]


@dataclass
class GeminiAdapter(BaseAdapter):
    """Observes Gemini CLI NDJSON output inside a Sandbox."""

    name: str = "gemini"
    capabilities: AdapterCapabilities = field(
        default_factory=lambda: AdapterCapabilities(
            streams_stdout=True,
            streams_stderr=True,
            observes_tool_calls=True,
            observes_file_changes=True,
            observes_shell_commands=True,
            supports_cancellation=True,
            supports_timeout=True,
        )
    )
    cli_binary: str = "gemini"
    # Headless coding-agent invocation: trust sandbox workspace, auto-approve
    # tools, stream NDJSON, prompt via -p.
    extra_args: tuple[str, ...] = (
        "--skip-trust",
        "--yolo",
        "--output-format",
        "stream-json",
        "-p",
    )
    stream_source: StreamSource | None = None
    _started_at: float | None = field(default=None, init=False, repr=False)
    _saw_completion: bool = field(default=False, init=False, repr=False)
    _saw_agent_error: bool = field(default=False, init=False, repr=False)
    _lines: list[str] = field(default_factory=list, init=False, repr=False)

    def initialize(self, context: ExecutionContext) -> None:
        if not context.working_directory:
            raise AdapterInitializationError("working_directory is required")
        self._reset_transient()

    def prepare(self, context: ExecutionContext) -> None:
        if not context.prompt.strip() and self.stream_source is None:
            raise AdapterInitializationError(
                "Prompt content is required for Gemini",
                details={"run_id": context.run.run_id},
            )

    def start(self, context: ExecutionContext) -> None:
        self._started_at = time.monotonic()
        self._saw_completion = False
        self._saw_agent_error = False
        if context.logger is not None:
            context.logger.info(
                "gemini_adapter_start",
                run_id=context.run.run_id,
                correlation_id=context.correlation_id,
            )

    def stream(self, context: ExecutionContext) -> Iterator[NativeObservation]:
        for line in self._iter_lines(context):
            self._check_bounds(context)
            self._lines.append(line)
            try:
                observations = parse_stream_line(line)
            except MalformedOutputError:
                yield observation_now(
                    ObservationKind.ERROR,
                    payload={
                        "message": "malformed stream line",
                        "line": line[:200],
                    },
                    raw=line,
                )
                continue
            for observation in observations:
                if observation.kind is ObservationKind.COMPLETION:
                    self._saw_completion = True
                    if observation.payload.get("status") == "agent_failed":
                        self._saw_agent_error = True
                if observation.kind is ObservationKind.ERROR:
                    self._saw_agent_error = True
                yield observation

    def finish(
        self,
        context: ExecutionContext,
        observations: tuple[NativeObservation, ...],
    ) -> AdapterOutcome:
        del observations
        if context.is_cancelled():
            return AdapterOutcome.CANCELLED
        if self._started_at is not None:
            elapsed = time.monotonic() - self._started_at
            if elapsed > context.config.timeout_seconds and not self._saw_completion:
                return AdapterOutcome.TIMED_OUT
        if self._saw_agent_error and self._saw_completion:
            return AdapterOutcome.AGENT_FAILED
        if self._saw_completion:
            return AdapterOutcome.COMPLETED
        return AdapterOutcome.AGENT_FAILED

    def cleanup(self, context: ExecutionContext) -> None:
        del context
        self._reset_transient()

    def _iter_lines(self, context: ExecutionContext) -> Iterator[str]:
        if self.stream_source is not None:
            yield from self.stream_source(context)
            return

        command = (self.cli_binary, *self.extra_args, context.prompt)
        result = context.sandbox_exec.execute(
            context.sandbox,
            ExecutionRequest(
                command=command,
                working_dir=context.working_directory,
                environment=dict(context.environment),
                timeout_seconds=context.config.timeout_seconds,
            ),
        )
        if result.timed_out:
            raise AdapterTimeoutError(
                "Gemini process timed out",
                details={
                    "run_id": context.run.run_id,
                    "timeout_seconds": context.config.timeout_seconds,
                },
            )
        for err_line in result.stderr.splitlines():
            if err_line.strip():
                yield json.dumps({"type": "error", "message": err_line})
        yield from result.stdout.splitlines()

    def _check_bounds(self, context: ExecutionContext) -> None:
        if context.is_cancelled():
            raise AdapterCancellationError(
                details={"run_id": context.run.run_id},
            )
        if self._started_at is None:
            return
        elapsed = time.monotonic() - self._started_at
        if elapsed > context.config.timeout_seconds:
            raise AdapterTimeoutError(
                "Gemini stream exceeded timeout",
                details={
                    "run_id": context.run.run_id,
                    "elapsed_seconds": elapsed,
                    "timeout_seconds": context.config.timeout_seconds,
                },
            )

    def _reset_transient(self) -> None:
        self._started_at = None
        self._saw_completion = False
        self._saw_agent_error = False
        self._lines.clear()
