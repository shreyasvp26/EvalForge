"""SdkAdapterBridge must surface AdapterOutcome as run failures."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from agent_eval_adapters.gemini import GeminiAdapter
from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.docker.fake import FakeDockerEngine
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import SandboxSpec
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause


class _CaptureStream:
    def submit_event(self, event: object) -> list[object]:
        del event
        return []

    def submit_artifact(self, artifact: object) -> object:
        return artifact


def _bridge_with_gemini(stream_lines: list[str]) -> tuple[SdkAdapterBridge, RunId]:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    registry = RunSandboxRegistry()
    run_id = RunId("run-bridge-outcome")
    handle = manager.create(
        SandboxSpec(image="evalforge/sandbox:local", working_dir="/workspace")
    )
    manager.start(handle)
    registry.register(run_id, handle)

    def factory() -> GeminiAdapter:
        def source(_ctx: ExecutionContext) -> Iterator[str]:
            yield from stream_lines

        return GeminiAdapter(stream_source=source)

    bridge = SdkAdapterBridge(
        stream=_CaptureStream(),  # type: ignore[arg-type]
        sandboxes=registry,
        manager=manager,
        adapter_factory=factory,
        run_metadata_factory=lambda rid: RunMetadata(
            run_id=rid.value,
            agent_version_id="agent-v1",
            adapter_version_id="adapter-v1",
            prompt_version_id="prompt-v1",
            case_version_id="case-v1",
        ),
        prompt="fix calculator.add",
    )
    return bridge, run_id


def test_bridge_finish_raises_on_agent_failed_rate_limit() -> None:
    lines = [
        json.dumps({"type": "error", "message": "Gemini API rate limit exceeded"}),
        json.dumps(
            {
                "type": "result",
                "status": "error",
                "error": {"message": "Gemini API rate limit exceeded"},
            }
        ),
    ]
    bridge, run_id = _bridge_with_gemini(lines)
    bridge.start(run_id)
    bridge.run(run_id)
    with pytest.raises(RecoverableExecutionError, match="rate limit") as exc_info:
        bridge.finish(run_id)
    assert exc_info.value.cause is FailureCause.ADAPTER_FAILURE


def test_bridge_finish_allows_completed() -> None:
    lines = [
        json.dumps({"type": "message", "role": "assistant", "content": "done"}),
        json.dumps({"type": "result", "status": "success"}),
    ]
    bridge, run_id = _bridge_with_gemini(lines)
    bridge.start(run_id)
    bridge.run(run_id)
    bridge.finish(run_id)  # must not raise
