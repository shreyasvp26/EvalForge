"""Single-invocation Adapter execution entry point."""

from __future__ import annotations

from dataclasses import dataclass

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
    emitter = EventEmitter(sink=sink)
    driver = LifecycleDriver(
        adapter=adapter,
        translator=translator or DefaultTranslator(),
        emitter=emitter,
    )
    outcome = driver.run(context)
    return AdapterResult(
        outcome=outcome,
        events_emitted=emitter.event_count,
        artifacts_emitted=emitter.artifact_count,
        emission_order=emitter.emission_order,
    )
