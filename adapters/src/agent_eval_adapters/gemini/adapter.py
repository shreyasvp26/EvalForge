"""Gemini CLI production Adapter — translation only."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from agent_eval_sandbox.models import ExecutionRequest

from agent_eval_adapters.gemini.errors import classify_gemini_cli_failure
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
    model_id: str | None = None
    """Exact model pin. When set, passed as ``--model`` to the Gemini CLI."""
    require_exact_model: bool = False
    """When True, refuse to start without an explicit model pin."""
    _started_at: float | None = field(default=None, init=False, repr=False)
    _saw_completion: bool = field(default=False, init=False, repr=False)
    _saw_agent_error: bool = field(default=False, init=False, repr=False)
    _failure_detail: str | None = field(default=None, init=False, repr=False)
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
        effective_model = (context.model_id or self.model_id or "").strip()
        if self.require_exact_model and not effective_model:
            raise AdapterInitializationError(
                "Exact model pin required for Gemini execution; "
                "refusing to use an implicit CLI default",
                details={"run_id": context.run.run_id},
            )
        if effective_model.lower() == "auto":
            raise AdapterInitializationError(
                "Gemini fixed routing cannot use model 'auto'",
                details={"run_id": context.run.run_id, "model_id": effective_model},
            )
        if effective_model:
            self.model_id = effective_model

    def start(self, context: ExecutionContext) -> None:
        self._started_at = time.monotonic()
        self._saw_completion = False
        self._saw_agent_error = False
        self._failure_detail = None
        if context.logger is not None:
            context.logger.info(
                "gemini_adapter_start",
                run_id=context.run.run_id,
                correlation_id=context.correlation_id,
                model_id=context.model_id or self.model_id,
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
                        detail = str(
                            observation.payload.get("subtype")
                            or observation.payload.get("message")
                            or "agent_failed"
                        )
                        self._failure_detail = self._failure_detail or detail
                if observation.kind is ObservationKind.ERROR:
                    self._saw_agent_error = True
                    message = str(observation.payload.get("message") or "error")
                    self._failure_detail = message
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
        if self._saw_agent_error:
            return AdapterOutcome.AGENT_FAILED
        if self._saw_completion:
            return AdapterOutcome.COMPLETED
        return AdapterOutcome.AGENT_FAILED

    def cleanup(self, context: ExecutionContext) -> None:
        del context
        self._reset_transient()

    def failure_detail(self) -> str | None:
        """Last actionable provider/CLI failure message, if any."""
        return self._failure_detail

    def _cli_command(self, context: ExecutionContext) -> tuple[str, ...]:
        model = (context.model_id or self.model_id or "").strip()
        if model:
            args = list(self.extra_args)
            try:
                p_index = args.index("-p")
            except ValueError:
                return (self.cli_binary, *args, "--model", model, context.prompt)
            return (
                self.cli_binary,
                *args[:p_index],
                "--model",
                model,
                *args[p_index:],
                context.prompt,
            )
        return (self.cli_binary, *self.extra_args, context.prompt)

    def _iter_lines(self, context: ExecutionContext) -> Iterator[str]:
        if self.stream_source is not None:
            yield from self.stream_source(context)
            return

        command = self._cli_command(context)
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

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        classified = classify_gemini_cli_failure(
            stderr=stderr,
            stdout=stdout,
            exit_code=result.exit_code,
        )

        # Preserve benign stderr as STDERR observations (not ERROR) so YOLO /
        # color / ripgrep notices do not fail a successful coding run.
        for err_line in stderr.splitlines():
            if err_line.strip():
                yield json.dumps({"type": "stderr", "content": err_line})

        yield from stdout.splitlines()

        if classified is not None:
            yield json.dumps({"type": "error", "message": classified})
            if not _stdout_has_result(stdout):
                yield json.dumps(
                    {
                        "type": "result",
                        "status": "error",
                        "error": {"message": classified},
                    }
                )

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
        self._failure_detail = None
        self._lines.clear()


def _stdout_has_result(stdout: str) -> bool:
    for line in stdout.splitlines():
        text = line.strip()
        if '"type":"result"' in text or '"type": "result"' in text:
            return True
    return False
