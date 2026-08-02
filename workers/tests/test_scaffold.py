"""Smoke tests for the Execution Worker runtime scaffold (Phase 1)."""

from __future__ import annotations

import agent_eval_workers
import agent_eval_workers.cancellation as cancellation
import agent_eval_workers.checkpoints as checkpoints
import agent_eval_workers.event_pipeline as event_pipeline
import agent_eval_workers.execution_engine as execution_engine
import agent_eval_workers.lifecycle as lifecycle
import agent_eval_workers.scheduler as scheduler
import agent_eval_workers.worker as worker


def test_package_importable() -> None:
    assert agent_eval_workers.__doc__ is not None


def test_runtime_subpackages_importable() -> None:
    packages = (
        worker,
        execution_engine,
        scheduler,
        lifecycle,
        cancellation,
        checkpoints,
        event_pipeline,
    )
    for package in packages:
        assert package.__doc__ is not None
        assert "Phase 1" in (package.__doc__ or "")
        assert "Must NOT" in (package.__doc__ or "")
