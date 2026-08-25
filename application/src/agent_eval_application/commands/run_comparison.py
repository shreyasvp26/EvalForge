"""Run comparison command."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CompareRunsCommand:
    actor: Actor
    run_ids: tuple[str, ...]
