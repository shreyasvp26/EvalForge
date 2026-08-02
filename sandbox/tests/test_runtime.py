"""Sandbox Runtime unit tests — mocked Docker engine."""

from __future__ import annotations

import tarfile
from io import BytesIO
from pathlib import Path

import pytest
from agent_eval_sandbox.docker.cleanup import ensure_destroyed, run_with_cleanup
from agent_eval_sandbox.docker.mounts import readonly_mount, workspace_mount
from agent_eval_sandbox.docker.networking import resolve_network
from agent_eval_sandbox.docker.resources import build_resource_host_config
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.exceptions import (
    SandboxCleanupError,
    SandboxCopyError,
    SandboxExecutionError,
    SandboxNotFoundError,
    SandboxProvisionError,
    SandboxStateError,
)
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import (
    ArtifactExportRequest,
    ArtifactKind,
    ExecutionRequest,
    MountSpec,
    NetworkMode,
    NetworkPolicy,
    ResourceLimits,
    SandboxSpec,
    SandboxState,
)
from docker_fakes import FakeDockerEngine


def _spec(**overrides: object) -> SandboxSpec:
    base = dict(
        image="evalforge/sandbox:test",
        working_dir="/workspace",
        environment={"FOO": "bar"},
        mounts=(workspace_mount("/tmp/repo"), readonly_mount("/tmp/tools", "/tools")),
        resources=ResourceLimits(
            cpu_cores=0.5,
            memory_bytes=256 * 1024 * 1024,
            disk_bytes=1024 * 1024 * 1024,
            timeout_seconds=30.0,
        ),
        network=NetworkPolicy(mode=NetworkMode.NONE),
        labels={"run": "test"},
    )
    base.update(overrides)
    return SandboxSpec(**base)  # type: ignore[arg-type]


def _runtime(
    engine: FakeDockerEngine | None = None,
) -> tuple[DockerSandbox, FakeDockerEngine]:
    fake = engine or FakeDockerEngine()
    return DockerSandbox(engine=fake), fake


def test_create_start_execute_stop_destroy() -> None:
    runtime, engine = _runtime()
    handle = runtime.create(_spec())
    assert handle.state is SandboxState.CREATED
    assert handle.container_id in engine.containers

    create_call = engine.create_calls[0]
    assert create_call["network_mode"] == "none"
    assert create_call["host_config"]["NanoCpus"] == 500_000_000
    assert create_call["host_config"]["Memory"] == 256 * 1024 * 1024
    mounts = create_call["host_config"]["Mounts"]
    assert mounts[0]["ReadOnly"] is False
    assert mounts[1]["ReadOnly"] is True
    assert create_call["labels"]["evalforge.sandbox"] == "true"

    handle = runtime.start(handle)
    assert handle.state is SandboxState.STARTED
    assert engine.containers[handle.container_id].started is True

    result = runtime.execute(
        handle,
        ExecutionRequest(command=("echo", "hi")),
    )
    assert result.exit_code == 0
    assert result.stdout == "ok"
    assert result.timed_out is False
    assert result.duration_seconds >= 0
    assert result.resource_usage.memory_bytes == 12_345_678

    handle = runtime.stop(handle)
    assert handle.state is SandboxState.STOPPED

    handle = runtime.destroy(handle)
    assert handle.state is SandboxState.DESTROYED
    assert handle.container_id in engine.removed_ids


def test_execute_timeout_returns_timed_out_result() -> None:
    runtime, _engine = _runtime(FakeDockerEngine(force_timeout=True))
    handle = runtime.start(runtime.create(_spec()))
    result = runtime.execute(
        handle,
        ExecutionRequest(command=("sleep", "999"), timeout_seconds=1.0),
    )
    assert result.timed_out is True
    assert result.exit_code == 124


def test_execute_timeout_raised_by_engine() -> None:
    runtime, _engine = _runtime(FakeDockerEngine(raise_timeout=True))
    handle = runtime.start(runtime.create(_spec()))
    result = runtime.execute(handle, ExecutionRequest(command=("sleep", "9")))
    assert result.timed_out is True
    assert result.exit_code == 124
    assert "timed out" in result.stderr


def test_execute_rejects_wrong_state() -> None:
    runtime, _engine = _runtime()
    handle = runtime.create(_spec())
    with pytest.raises(SandboxStateError):
        runtime.execute(handle, ExecutionRequest(command=("true",)))


def test_execute_failure_path() -> None:
    runtime, _engine = _runtime(FakeDockerEngine(fail_exec=True))
    handle = runtime.start(runtime.create(_spec()))
    with pytest.raises(SandboxExecutionError):
        runtime.execute(handle, ExecutionRequest(command=("boom",)))


def test_copy_out_file_and_log(tmp_path: Path) -> None:
    runtime, engine = _runtime()
    handle = runtime.start(runtime.create(_spec()))
    engine.seed_file(handle.container_id, "/workspace/out/result.txt", b"hello\n")

    exported = runtime.copy_out(
        handle,
        ArtifactExportRequest(
            container_path="/workspace/out/result.txt",
            kind=ArtifactKind.FILE,
            destination=str(tmp_path / "result.txt"),
        ),
    )
    assert exported.content == b"hello\n"
    assert exported.size_bytes == 6
    assert (tmp_path / "result.txt").read_bytes() == b"hello\n"

    log = runtime.copy_out(
        handle,
        ArtifactExportRequest(
            container_path="/workspace/logs/run.log",
            kind=ArtifactKind.LOG,
        ),
    )
    assert b"line1" in log.content


def test_copy_out_directory_returns_tar() -> None:
    runtime, engine = _runtime()
    handle = runtime.start(runtime.create(_spec()))
    engine.seed_file(handle.container_id, "/workspace/out/a.txt", b"a")
    engine.seed_file(handle.container_id, "/workspace/out/b.txt", b"b")

    exported = runtime.copy_out(
        handle,
        ArtifactExportRequest(
            container_path="/workspace/out",
            kind=ArtifactKind.DIRECTORY,
        ),
    )
    assert exported.kind is ArtifactKind.DIRECTORY
    with tarfile.open(fileobj=BytesIO(exported.content), mode="r:*") as tar:
        names = tar.getnames()
    assert any(name.endswith("a.txt") for name in names)
    assert any(name.endswith("b.txt") for name in names)


def test_copy_out_failure() -> None:
    runtime, _engine = _runtime(FakeDockerEngine(fail_archive=True))
    handle = runtime.start(runtime.create(_spec()))
    with pytest.raises(SandboxCopyError):
        runtime.copy_out(
            handle,
            ArtifactExportRequest(container_path="/missing"),
        )


def test_create_failure() -> None:
    runtime, _engine = _runtime(FakeDockerEngine(fail_create=True))
    with pytest.raises(SandboxProvisionError):
        runtime.create(_spec())


def test_restart_after_stop() -> None:
    runtime, engine = _runtime()
    handle = runtime.start(runtime.create(_spec()))
    handle = runtime.stop(handle)
    assert handle.state is SandboxState.STOPPED
    handle = runtime.start(handle)
    assert handle.state is SandboxState.STARTED
    assert engine.containers[handle.container_id].started is True
    result = runtime.execute(handle, ExecutionRequest(command=("true",)))
    assert result.exit_code == 0


def test_destroy_is_idempotent() -> None:
    runtime, _engine = _runtime()
    handle = runtime.start(runtime.create(_spec()))
    handle = runtime.destroy(handle)
    again = runtime.destroy(handle)
    assert again.state is SandboxState.DESTROYED


def test_cleanup_ensure_destroyed_after_failure() -> None:
    runtime, engine = _runtime()
    handle = runtime.start(runtime.create(_spec()))

    def boom(_: object) -> None:
        raise RuntimeError("worker interrupted")

    with pytest.raises(RuntimeError, match="worker interrupted"):
        run_with_cleanup(engine, handle, boom)

    assert handle.container_id in engine.removed_ids


def test_ensure_destroyed_when_stop_fails() -> None:
    engine = FakeDockerEngine(fail_stop=True)
    runtime = DockerSandbox(engine=engine)
    handle = runtime.start(runtime.create(_spec()))
    destroyed = ensure_destroyed(engine, handle)
    assert destroyed.state is SandboxState.DESTROYED
    assert handle.container_id in engine.removed_ids


def test_manager_session_always_cleans_up() -> None:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))

    with manager.session(_spec()) as handle:
        assert handle.state is SandboxState.STARTED
        result = manager.execute(handle, ExecutionRequest(command=("echo", "x")))
        assert result.exit_code == 0
        container_id = handle.container_id

    assert container_id in engine.removed_ids
    assert manager.active() == {}


def test_manager_session_cleans_up_on_exception() -> None:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))

    with pytest.raises(RuntimeError, match="boom"):
        with manager.session(_spec()) as handle:
            container_id = handle.container_id
            raise RuntimeError("boom")

    assert container_id in engine.removed_ids


def test_manager_cleanup_all() -> None:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    h1 = manager.start(manager.create(_spec(name="one")))
    h2 = manager.start(manager.create(_spec(name="two")))
    destroyed = manager.cleanup_all()
    assert set(destroyed) == {h1.id, h2.id}
    assert manager.active() == {}


def test_manager_cleanup_all_reports_failures() -> None:
    engine = FakeDockerEngine(fail_remove=True)
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    manager.start(manager.create(_spec()))
    with pytest.raises(SandboxCleanupError) as exc_info:
        manager.cleanup_all()
    assert "failures" in (exc_info.value.details or {})


def test_manager_unknown_handle() -> None:
    manager = SandboxManager(runtime=DockerSandbox(engine=FakeDockerEngine()))
    with pytest.raises(SandboxNotFoundError):
        manager.get("missing")


def test_resource_limits_validation() -> None:
    with pytest.raises(ValueError):
        build_resource_host_config(ResourceLimits(cpu_cores=0))
    with pytest.raises(ValueError):
        build_resource_host_config(ResourceLimits(memory_bytes=0))


def test_network_custom_requires_name() -> None:
    with pytest.raises(SandboxProvisionError):
        resolve_network(NetworkPolicy(mode=NetworkMode.CUSTOM))


def test_network_bridge_and_custom() -> None:
    mode, cfg, dns = resolve_network(
        NetworkPolicy(mode=NetworkMode.BRIDGE, dns=("1.1.1.1",))
    )
    assert mode == "bridge"
    assert cfg is None
    assert dns == ["1.1.1.1"]

    mode, cfg, _dns = resolve_network(
        NetworkPolicy(mode=NetworkMode.CUSTOM, network_name="evalforge-egress")
    )
    assert mode is None
    assert cfg is not None
    assert "evalforge-egress" in cfg["EndpointsConfig"]


def test_mount_helpers() -> None:
    assert workspace_mount("/repo").target == "/workspace"
    assert readonly_mount("/cache", "/cache").read_only is True
    with pytest.raises(ValueError):
        from agent_eval_sandbox.docker.mounts import build_mounts

        build_mounts((MountSpec(source="", target="/x"),))
