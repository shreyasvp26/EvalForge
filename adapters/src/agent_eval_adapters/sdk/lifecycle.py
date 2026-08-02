"""Adapter lifecycle phases and driver."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from enum import StrEnum

from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.emitter import EventEmitter
from agent_eval_adapters.sdk.exceptions import (
    AdapterCancellationError,
    AdapterError,
    AdapterInitializationError,
    AdapterTimeoutError,
)
from agent_eval_adapters.sdk.models import AdapterOutcome, NativeObservation
from agent_eval_adapters.sdk.translator import Translator


class AdapterPhase(StrEnum):
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    PREPARED = "prepared"
    STARTED = "started"
    STREAMING = "streaming"
    FINISHED = "finished"
    CLEANED_UP = "cleaned_up"
    FAILED = "failed"


@dataclass
class LifecycleDriver:
    """Drives initialize → prepare → start → stream → finish → cleanup.

    Every invocation is stateless from the Adapter's perspective: the driver
    holds phase state for one call only and does not reuse Adapter instances
    across runs unless the Adapter itself is explicitly designed as a factory.
    """

    adapter: Adapter
    translator: Translator
    emitter: EventEmitter
    phase: AdapterPhase = AdapterPhase.UNINITIALIZED
    outcome: AdapterOutcome | None = None
    _observations: list[NativeObservation] = field(default_factory=list)

    def run(self, context: ExecutionContext) -> AdapterOutcome:
        try:
            self._initialize(context)
            self._prepare(context)
            self._start(context)
            self._stream(context)
            self._finish(context)
            return self.outcome or AdapterOutcome.COMPLETED
        except AdapterCancellationError:
            self.outcome = AdapterOutcome.CANCELLED
            self.phase = AdapterPhase.FAILED
            self.emitter.emit_error("adapter cancelled")
            return AdapterOutcome.CANCELLED
        except AdapterTimeoutError as exc:
            self.outcome = AdapterOutcome.TIMED_OUT
            self.phase = AdapterPhase.FAILED
            self.emitter.emit_error(str(exc), details=exc.details)
            return AdapterOutcome.TIMED_OUT
        except AdapterError as exc:
            self.outcome = AdapterOutcome.ADAPTER_FAILED
            self.phase = AdapterPhase.FAILED
            self.emitter.emit_error(str(exc), details=exc.details)
            raise
        finally:
            self._cleanup(context)

    def _initialize(self, context: ExecutionContext) -> None:
        self._check_cancel(context)
        try:
            self.adapter.initialize(context)
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdapterInitializationError(
                f"Adapter initialize failed: {exc}",
                cause=exc,
            ) from exc
        self.phase = AdapterPhase.INITIALIZED

    def _prepare(self, context: ExecutionContext) -> None:
        self._check_cancel(context)
        try:
            self.adapter.prepare(context)
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdapterInitializationError(
                f"Adapter prepare failed: {exc}",
                cause=exc,
            ) from exc
        self.phase = AdapterPhase.PREPARED

    def _start(self, context: ExecutionContext) -> None:
        self._check_cancel(context)
        self.adapter.start(context)
        self.phase = AdapterPhase.STARTED

    def _stream(self, context: ExecutionContext) -> None:
        self.phase = AdapterPhase.STREAMING
        stream: Iterator[NativeObservation] = self.adapter.stream(context)
        for observation in stream:
            self._check_cancel(context)
            self._observations.append(observation)
            artifacts = tuple(self.translator.artifacts_for(observation, context))
            artifact_ids = tuple(a.artifact_id for a in artifacts)
            for artifact in artifacts:
                self.emitter.emit_artifact(artifact)
            for event in self.translator.translate(observation, context):
                if artifact_ids and not event.artifact_ids:
                    event = replace(event, artifact_ids=artifact_ids)
                self.emitter.emit_event(event)
            progress = self.translator.progress_for(observation, context)
            if progress is not None:
                self.emitter.emit_progress(progress)

    def _finish(self, context: ExecutionContext) -> None:
        outcome = self.adapter.finish(context, tuple(self._observations))
        self.outcome = outcome
        self.phase = AdapterPhase.FINISHED

    def _cleanup(self, context: ExecutionContext) -> None:
        try:
            self.adapter.cleanup(context)
        finally:
            if self.phase is not AdapterPhase.FAILED:
                self.phase = AdapterPhase.CLEANED_UP

    def _check_cancel(self, context: ExecutionContext) -> None:
        if context.is_cancelled():
            raise AdapterCancellationError(
                details={"run_id": context.run.run_id},
            )
