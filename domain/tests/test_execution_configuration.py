"""Domain tests for persisted execution configuration."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import RunId, SandboxId
from agent_eval_domain.execution.configuration import (
    ExecutionConfiguration,
    ExecutionMode,
    sanitize_execution_metadata,
)
from agent_eval_domain.execution.run import EvaluationRun
from helpers import make_direct_run_pins


def test_sanitize_drops_non_allowlisted_and_secretish_values() -> None:
    cleaned = sanitize_execution_metadata(
        {
            "adapter_key": "gemini_cli",
            "api_key": "sk-secret",
            "GEMINI_API_KEY": "abc",
            "sandbox_engine": "docker",
            "notes": "password=hunter2",
        }
    )
    assert cleaned == {
        "adapter_key": "gemini_cli",
        "sandbox_engine": "docker",
    }


def test_record_execution_configuration_while_running() -> None:
    run = EvaluationRun.create(run_id=RunId("run-1"), pins=make_direct_run_pins())
    run.queue()
    run.start(sandbox_id=SandboxId("sbx-1"))
    run.record_execution_configuration(
        ExecutionConfiguration(
            mode=ExecutionMode.LIVE,
            metadata={
                "adapter_key": "gemini_cli",
                "adapter_name": "Gemini CLI",
                "api_key": "should-drop",
            },
        )
    )
    assert run.execution_mode is ExecutionMode.LIVE
    assert run.execution_metadata == {
        "adapter_key": "gemini_cli",
        "adapter_name": "Gemini CLI",
    }


def test_execution_configuration_is_immutable() -> None:
    run = EvaluationRun.create(run_id=RunId("run-1"), pins=make_direct_run_pins())
    run.queue()
    run.record_execution_configuration(
        ExecutionConfiguration(mode=ExecutionMode.DETERMINISTIC, metadata={})
    )
    with pytest.raises(InvariantViolation, match="immutable"):
        run.record_execution_configuration(
            ExecutionConfiguration(mode=ExecutionMode.LIVE, metadata={})
        )


def test_execution_configuration_idempotent_same_payload() -> None:
    run = EvaluationRun.create(run_id=RunId("run-1"), pins=make_direct_run_pins())
    run.queue()
    cfg = ExecutionConfiguration(
        mode=ExecutionMode.DETERMINISTIC,
        metadata={"adapter_key": "claude_code"},
    )
    run.record_execution_configuration(cfg)
    run.record_execution_configuration(cfg)
    assert run.execution_mode is ExecutionMode.DETERMINISTIC
