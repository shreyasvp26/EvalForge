"""Single-invocation Adapter execution entry point."""

from __future__ import annotations

import time
from dataclasses import dataclass

from agent_eval_shared.metrics import observe_adapter_run
from agent_eval_shared.tracing import start_span

from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.emitter import EventEmitter
from agent_eval_adapters.sdk.lifecycle import LifecycleDriver
from agent_eval_adapters.sdk.models import AdapterOutcome
from agent_eval_adapters.sdk.ports import EventSink
from agent_eval_adapters.sdk.translator import DefaultTranslator, Translator


@dataclass(frozen=True, slots=True)
class AdapterResult:
    outcome: AdapterOutcome
    events_emitted: int
    artifacts_emitted: int
    emission_order: tuple[str, ...]


def run_adapter(
    adapter: Adapter,
    context: ExecutionContext,
    sink: EventSink,
    *,
    translator: Translator | None = None,
) -> AdapterResult:
    """Run one complete Adapter lifecycle against ``context``.

    Stateless: creates a fresh emitter + lifecycle driver per call.
    """
    started = time.perf_counter()
    with start_span(
        "adapter.run",
        tracer_name="evalforge.adapter",
        attributes={"run.id": context.run.run_id},
    ):
        emitter = EventEmitter(sink=sink)
        driver = LifecycleDriver(
            adapter=adapter,
            translator=translator or DefaultTranslator(),
            emitter=emitter,
        )
        outcome = driver.run(context)
    result = AdapterResult(
        outcome=outcome,
        events_emitted=emitter.event_count,
        artifacts_emitted=emitter.artifact_count,
        emission_order=emitter.emission_order,
    )
    observe_adapter_run(
        outcome=outcome.value,
        duration_seconds=time.perf_counter() - started,
        events=result.events_emitted,
        artifacts=result.artifacts_emitted,
    )
    return result
