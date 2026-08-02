"""Test doubles for Adapter integration tests — mocked Sandbox only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from agent_eval_adapters.sdk.models import (
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
)
from agent_eval_adapters.sdk.ports import CancellationPort, EventSink
from agent_eval_sandbox.models import (
    ExecutionRequest,
    ExecutionResult,
    ResourceLimits,
    ResourceUsage,
    SandboxHandle,
    SandboxSpec,
    SandboxState,
)


@dataclass
class RecordingSink(EventSink):
    events: list[EmittedEvent] = field(default_factory=list)
    artifacts: list[EmittedArtifact] = field(default_factory=list)
    progress: list[EmittedProgress] = field(default_factory=list)
    errors: list[tuple[str, Mapping[str, object] | None]] = field(default_factory=list)

    def on_event(self, event: EmittedEvent) -> None:
        self.events.append(event)

    def on_artifact(self, artifact: EmittedArtifact) -> None:
        self.artifacts.append(artifact)

    def on_progress(self, progress: EmittedProgress) -> None:
        self.progress.append(progress)

    def on_error(
        self,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.errors.append((message, details))


@dataclass
class FlagCancellation(CancellationPort):
    cancelled: bool = False

    def is_cancelled(self) -> bool:
        return self.cancelled


@dataclass
class MockSandboxExec:
    """Mocked SandboxExecPort — never talks to Docker or Workers."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    commands: list[tuple[str, ...]] = field(default_factory=list)

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        del handle
        self.commands.append(request.command)
        return ExecutionResult(
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            duration_seconds=0.01,
            timed_out=self.timed_out,
            resource_usage=ResourceUsage(duration_seconds=0.01),
        )


def make_handle() -> SandboxHandle:
    return SandboxHandle(
        id="sbx-test",
        container_id="ctr-test",
        state=SandboxState.STARTED,
        spec=SandboxSpec(
            image="test",
            working_dir="/workspace",
            resources=ResourceLimits(timeout_seconds=60.0),
        ),
    )
