"""AdapterPort ← Adapter SDK (Workers never embed Claude-specific logic)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Protocol

from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.context import ExecutionConfig, ExecutionContext
from agent_eval_adapters.sdk.emitter import EventEmitter
from agent_eval_adapters.sdk.exceptions import (
    AdapterCancellationError,
    AdapterError,
    AdapterTimeoutError,
)
from agent_eval_adapters.sdk.models import (
    AdapterOutcome,
    NativeObservation,
    ObservationKind,
    RunMetadata,
)
from agent_eval_adapters.sdk.ports import CancellationPort
from agent_eval_adapters.sdk.translator import DefaultTranslator, Translator
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest, ExecutionResult, SandboxHandle
from agent_eval_shared.metrics import observe_adapter_run
from agent_eval_shared.tracing import start_span

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.event_sink import PipelineEventSink
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.mocks.stream import EventStreamPort


def _outcome_failure_detail(
    adapter: Adapter,
    observations: list[NativeObservation],
) -> str:
    detail_fn = getattr(adapter, "failure_detail", None)
    if callable(detail_fn):
        detail = detail_fn()
        if detail:
            return str(detail)
    for observation in reversed(observations):
        if observation.kind is ObservationKind.ERROR:
            message = observation.payload.get("message")
            if message:
                return str(message)
        if (
            observation.kind is ObservationKind.COMPLETION
            and observation.payload.get("status") == "agent_failed"
        ):
            return str(
                observation.payload.get("subtype")
                or observation.payload.get("message")
                or "agent_failed"
            )
    return "adapter reported agent failure"


AdapterFactory = Callable[[], Adapter]
AdapterHook = Callable[[RunId], None]
RunMetadataFactory = Callable[[RunId], RunMetadata]
PromptFactory = Callable[[RunId], str]
AdapterFactoryResolver = Callable[[RunId], AdapterFactory]
WorkingDirectoryFactory = Callable[[RunId], str]
ModelIdFactory = Callable[[RunId], str | None]
EnvironmentFactory = Callable[[RunId], dict[str, str]]


class _ArtifactStore(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str) -> object: ...


@dataclass
class ManagerSandboxExec:
    """``SandboxExecPort`` wrapping ``SandboxManager.execute``."""

    manager: SandboxManager

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        return self.manager.execute(handle, request)


@dataclass
class RegistryCancellation:
    """Adapter cancellation signal backed by the Worker cancel registry."""

    registry: object
    run_id: RunId

    def is_cancelled(self) -> bool:
        return bool(self.registry.is_cancel_requested(self.run_id))  # type: ignore[attr-defined]


@dataclass
class _Session:
    context: ExecutionContext
    adapter: Adapter
    emitter: EventEmitter
    translator: Translator
    observations: list[NativeObservation] = field(default_factory=list)
    sink: PipelineEventSink | None = None


def default_run_metadata(run_id: RunId) -> RunMetadata:
    return RunMetadata(
        run_id=run_id.value,
        agent_version_id="agent-v1",
        adapter_version_id="adapter-v1",
        prompt_version_id="prompt-v1",
        case_version_id="case-v1",
    )


@dataclass
class SdkAdapterBridge:
    """``AdapterPort`` that drives the Adapter SDK lifecycle in Engine steps.

    ``start`` / ``run`` / ``finish`` map to SDK phases so checkpoint resume at
    ``ADAPTER_STARTING`` remains valid. Vendor Adapters (e.g. Claude Code) are
    supplied via ``adapter_factory`` at composition time only.
    """

    stream: EventStreamPort
    sandboxes: RunSandboxRegistry
    manager: SandboxManager
    adapter_factory: AdapterFactory
    adapter_factory_resolver: AdapterFactoryResolver | None = None
    cancellation: object | None = None
    object_storage: _ArtifactStore | None = None
    run_metadata_factory: RunMetadataFactory = field(default=default_run_metadata)
    prompt: str = "solve the case"
    prompt_factory: PromptFactory | None = None
    model_id_factory: ModelIdFactory | None = None
    working_directory: str = "/workspace"
    working_directory_factory: WorkingDirectoryFactory | None = None
    environment: dict[str, str] = field(default_factory=dict)
    environment_factory: EnvironmentFactory | None = None
    fail_on_run: bool = False
    after_start: AdapterHook | None = None
    before_run: AdapterHook | None = None
    after_run: AdapterHook | None = None
    started: list[RunId] = field(default_factory=list)
    ran: list[RunId] = field(default_factory=list)
    finished: list[RunId] = field(default_factory=list)
    _sessions: dict[str, _Session] = field(default_factory=dict, repr=False)

    def _resolve_prompt(self, run_id: RunId) -> str:
        if self.prompt_factory is not None:
            return self.prompt_factory(run_id)
        return self.prompt

    def _resolve_working_directory(self, run_id: RunId) -> str:
        if self.working_directory_factory is not None:
            return self.working_directory_factory(run_id)
        return self.working_directory

    def _resolve_model_id(self, run_id: RunId) -> str | None:
        if self.model_id_factory is not None:
            return self.model_id_factory(run_id)
        return None

    def _resolve_environment(self, run_id: RunId) -> dict[str, str]:
        if self.environment_factory is not None:
            return dict(self.environment_factory(run_id))
        return dict(self.environment)

    def _resolve_adapter(self, run_id: RunId) -> Adapter:
        if self.adapter_factory_resolver is not None:
            return self.adapter_factory_resolver(run_id)()
        return self.adapter_factory()

    def start(self, run_id: RunId) -> None:
        try:
            handle = self.sandboxes.get(run_id)
            sink = PipelineEventSink(
                stream=self.stream,
                run_id=run_id,
                object_storage=self.object_storage,
            )
            adapter = self._resolve_adapter(run_id)
            cancel: CancellationPort | None = None
            if self.cancellation is not None:
                cancel = RegistryCancellation(registry=self.cancellation, run_id=run_id)
            context = ExecutionContext(
                working_directory=self._resolve_working_directory(run_id),
                sandbox=handle,
                sandbox_exec=ManagerSandboxExec(manager=self.manager),
                environment=self._resolve_environment(run_id),
                run=self.run_metadata_factory(run_id),
                correlation_id=f"corr-{run_id.value}",
                config=ExecutionConfig(),
                prompt=self._resolve_prompt(run_id),
                cancellation=cancel,
                model_id=self._resolve_model_id(run_id),
            )
            emitter = EventEmitter(sink=sink)
            translator = DefaultTranslator()
            adapter.initialize(context)
            adapter.prepare(context)
            adapter.start(context)
            self._sessions[run_id.value] = _Session(
                context=context,
                adapter=adapter,
                emitter=emitter,
                translator=translator,
                sink=sink,
            )
            self.started.append(run_id)
            if self.after_start is not None:
                self.after_start(run_id)
        except RecoverableExecutionError:
            raise
        except AdapterError as exc:
            raise RecoverableExecutionError(
                f"Adapter start failed for {run_id.value}: {exc}",
                cause=FailureCause.ADAPTER_FAILURE,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RecoverableExecutionError(
                f"Adapter start failed for {run_id.value}: {exc}",
                cause=FailureCause.ADAPTER_FAILURE,
            ) from exc

    def run(self, run_id: RunId) -> None:
        if self.before_run is not None:
            self.before_run(run_id)
        if self.fail_on_run:
            observe_adapter_run(outcome="failed", duration_seconds=0.0)
            raise RecoverableExecutionError(
                f"Adapter failed for {run_id.value}",
                cause=FailureCause.ADAPTER_FAILURE,
            )
        session = self._sessions.get(run_id.value)
        if session is None:
            observe_adapter_run(outcome="failed", duration_seconds=0.0)
            raise RecoverableExecutionError(
                f"Adapter run without start for {run_id.value}",
                cause=FailureCause.ADAPTER_FAILURE,
            )
        started = time.perf_counter()
        try:
            with start_span(
                "adapter.bridge.run",
                tracer_name="evalforge.adapter",
                attributes={"run.id": run_id.value},
            ):
                for observation in session.adapter.stream(session.context):
                    session.observations.append(observation)
                    artifacts = tuple(
                        session.translator.artifacts_for(observation, session.context)
                    )
                    artifact_ids = tuple(a.artifact_id for a in artifacts)
                    for artifact in artifacts:
                        session.emitter.emit_artifact(artifact)
                    for event in session.translator.translate(
                        observation, session.context
                    ):
                        if artifact_ids and not event.artifact_ids:
                            event = replace(event, artifact_ids=artifact_ids)
                        session.emitter.emit_event(event)
                    progress = session.translator.progress_for(
                        observation, session.context
                    )
                    if progress is not None:
                        session.emitter.emit_progress(progress)
            self.ran.append(run_id)
            observe_adapter_run(
                outcome="succeeded",
                duration_seconds=time.perf_counter() - started,
                events=session.emitter.event_count,
                artifacts=session.emitter.artifact_count,
            )
            if self.after_run is not None:
                self.after_run(run_id)
        except AdapterCancellationError as exc:
            observe_adapter_run(
                outcome="cancelled",
                duration_seconds=time.perf_counter() - started,
            )
            raise RecoverableExecutionError(
                f"Adapter cancelled for {run_id.value}",
                cause=FailureCause.WORKER_FAILURE,
            ) from exc
        except AdapterTimeoutError as exc:
            observe_adapter_run(
                outcome="timeout",
                duration_seconds=time.perf_counter() - started,
            )
            raise RecoverableExecutionError(
                f"Adapter timed out for {run_id.value}: {exc}",
                cause=FailureCause.TIMEOUT,
            ) from exc
        except AdapterError as exc:
            observe_adapter_run(
                outcome="failed",
                duration_seconds=time.perf_counter() - started,
            )
            raise RecoverableExecutionError(
                f"Adapter failed for {run_id.value}: {exc}",
                cause=FailureCause.ADAPTER_FAILURE,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            observe_adapter_run(
                outcome="failed",
                duration_seconds=time.perf_counter() - started,
            )
            raise RecoverableExecutionError(
                f"Adapter failed for {run_id.value}: {exc}",
                cause=FailureCause.ADAPTER_FAILURE,
            ) from exc

    def finish(self, run_id: RunId) -> None:
        session = self._sessions.pop(run_id.value, None)
        self.finished.append(run_id)
        if session is None:
            return
        try:
            outcome = session.adapter.finish(
                session.context, tuple(session.observations)
            )
            if outcome is AdapterOutcome.COMPLETED:
                return
            if outcome is AdapterOutcome.TIMED_OUT:
                raise RecoverableExecutionError(
                    f"Adapter timed out for {run_id.value}",
                    cause=FailureCause.TIMEOUT,
                )
            if outcome is AdapterOutcome.CANCELLED:
                raise RecoverableExecutionError(
                    f"Adapter cancelled for {run_id.value}",
                    cause=FailureCause.WORKER_FAILURE,
                )
            detail = _outcome_failure_detail(session.adapter, session.observations)
            raise RecoverableExecutionError(
                f"Adapter failed for {run_id.value}: {detail}",
                cause=FailureCause.ADAPTER_FAILURE,
            )
        finally:
            session.adapter.cleanup(session.context)
