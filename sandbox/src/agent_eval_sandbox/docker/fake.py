"""In-memory fake Docker engine for tests and local execution without a daemon.

Labeled explicitly as test / local infrastructure — not a production Docker
backend. Use ``DockerPyEngine.from_env()`` when a real daemon is available.
"""

from __future__ import annotations

import io
import tarfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import Event
from typing import Any
from uuid import uuid4

from agent_eval_sandbox.exceptions import SandboxTimeoutError


@dataclass
class FakeContainer:
    image: str
    command: list[str]
    working_dir: str
    environment: dict[str, str]
    labels: dict[str, str]
    host_config: dict[str, object]
    network_mode: str | None = None
    networking_config: dict[str, object] | None = None
    name: str | None = None
    started: bool = False
    removed: bool = False
    filesystem: dict[str, bytes] = field(default_factory=dict)
    exec_log: list[list[str]] = field(default_factory=list)


@dataclass
class FakeDockerEngine:
    """Deterministic ``DockerEngine`` — no real Docker daemon required."""

    containers: dict[str, FakeContainer] = field(default_factory=dict)
    fail_create: bool = False
    fail_start: bool = False
    fail_stop: bool = False
    fail_remove: bool = False
    fail_exec: bool = False
    fail_archive: bool = False
    exec_delay_seconds: float = 0.0
    exec_exit_code: int = 0
    exec_stdout: bytes = b"ok"
    exec_stderr: bytes = b""
    force_timeout: bool = False
    raise_timeout: bool = False
    stats_payload: dict[str, object] = field(
        default_factory=lambda: {
            "memory_stats": {"usage": 12_345_678},
            "cpu_stats": {
                "cpu_usage": {"total_usage": 2000, "percpu_usage": [1000, 1000]},
                "system_cpu_usage": 10_000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 1000, "percpu_usage": [500, 500]},
                "system_cpu_usage": 5_000,
                "online_cpus": 2,
            },
        }
    )
    create_calls: list[dict[str, Any]] = field(default_factory=list)
    removed_ids: list[str] = field(default_factory=list)
    _block_exec: Event | None = field(default=None, repr=False)
    # Simulated git HEAD for repository materialization tests.
    checked_out_sha: str | None = None
    fail_git: bool = False
    git_fail_message: bytes = b"fake git failure"

    def create_container(
        self,
        *,
        image: str,
        name: str | None,
        command: list[str],
        working_dir: str,
        environment: Mapping[str, str],
        labels: Mapping[str, str],
        host_config: Mapping[str, object],
        networking_config: Mapping[str, object] | None = None,
        network_mode: str | None = None,
    ) -> str:
        self.create_calls.append(
            {
                "image": image,
                "name": name,
                "command": command,
                "working_dir": working_dir,
                "environment": dict(environment),
                "labels": dict(labels),
                "host_config": dict(host_config),
                "networking_config": networking_config,
                "network_mode": network_mode,
            }
        )
        if self.fail_create:
            raise RuntimeError("fake create failure")
        container_id = f"ctr-{uuid4().hex[:12]}"
        self.containers[container_id] = FakeContainer(
            image=image,
            command=command,
            working_dir=working_dir,
            environment=dict(environment),
            labels=dict(labels),
            host_config=dict(host_config),
            network_mode=network_mode,
            networking_config=(
                dict(networking_config) if networking_config is not None else None
            ),
            name=name,
            filesystem={
                "/workspace/README.md": b"# repo\n",
                "/workspace/logs/run.log": b"line1\nline2\n",
                "/workspace/out/result.txt": b"result\n",
            },
        )
        return container_id

    def start_container(self, container_id: str) -> None:
        if self.fail_start:
            raise RuntimeError("fake start failure")
        self.containers[container_id].started = True

    def stop_container(self, container_id: str, *, timeout: float) -> None:
        del timeout
        if self.fail_stop:
            raise RuntimeError("fake stop failure")
        container = self.containers[container_id]
        container.started = False

    def remove_container(self, container_id: str, *, force: bool = True) -> None:
        del force
        if self.fail_remove:
            raise RuntimeError("fake remove failure")
        container = self.containers.get(container_id)
        if container is None:
            raise RuntimeError(f"No such container: {container_id}")
        container.removed = True
        container.started = False
        self.removed_ids.append(container_id)
        del self.containers[container_id]

    def exec_run(
        self,
        container_id: str,
        *,
        command: list[str],
        working_dir: str | None,
        environment: Mapping[str, str] | None,
        timeout_seconds: float | None,
    ) -> tuple[int, bytes, bytes, bool]:
        del working_dir, environment
        container = self.containers[container_id]
        container.exec_log.append(list(command))
        if self.fail_exec:
            raise RuntimeError("fake exec failure")
        if self.raise_timeout:
            raise SandboxTimeoutError(
                "forced timeout",
                details={"timeout_seconds": timeout_seconds},
            )
        if self._block_exec is not None:
            waited = self._block_exec.wait(
                timeout=timeout_seconds if timeout_seconds is not None else 30.0
            )
            if not waited and timeout_seconds is not None:
                return 124, b"", b"timed out", True
        if self.exec_delay_seconds:
            time.sleep(self.exec_delay_seconds)
        if self.force_timeout:
            return 124, b"", b"timed out", True

        git_result = self._maybe_handle_git(command)
        if git_result is not None:
            return git_result

        return self.exec_exit_code, self.exec_stdout, self.exec_stderr, False

    def _maybe_handle_git(
        self, command: list[str]
    ) -> tuple[int, bytes, bytes, bool] | None:
        if not command:
            return None
        if command[0] == "test" and len(command) >= 3 and command[1] == "-d":
            # Subdirectory exists checks succeed by default in fake sandboxes.
            return 0, b"", b"", False
        if command[0] == "sh":
            # Workspace cleanup / shell helpers used by materializer.
            return 0, b"", b"", False
        if command[0] != "git" and not (len(command) >= 2 and command[0] == "rm"):
            return None
        if self.fail_git and command[0] == "git":
            return 1, b"", self.git_fail_message, False
        if command[0] == "rm":
            return 0, b"", b"", False
        # git …
        if "checkout" in command:
            # git … checkout --detach <sha>
            sha = command[-1]
            if sha not in {"--detach", "checkout"}:
                self.checked_out_sha = sha
            return 0, b"", b"", False
        if "rev-parse" in command:
            sha = (self.checked_out_sha or "deadbeef").encode()
            return 0, sha + b"\n", b"", False
        if command[0] == "git":
            return 0, b"", b"", False
        return None

    def get_archive(self, container_id: str, path: str) -> bytes:
        if self.fail_archive:
            raise RuntimeError("fake archive failure")
        container = self.containers[container_id]
        matches = {
            key: value
            for key, value in container.filesystem.items()
            if key == path or key.startswith(path.rstrip("/") + "/")
        }
        if not matches and path in container.filesystem:
            matches = {path: container.filesystem[path]}
        if not matches:
            if path.endswith("/") or path in {"/workspace", "/workspace/out"}:
                matches = {
                    f"{path.rstrip('/')}/.keep": b"",
                }
            else:
                raise FileNotFoundError(path)

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name, data in matches.items():
                arcname = name.lstrip("/")
                info = tarfile.TarInfo(name=arcname)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return buffer.getvalue()

    def container_stats(self, container_id: str) -> Mapping[str, object]:
        if container_id not in self.containers:
            raise RuntimeError(f"No such container: {container_id}")
        return dict(self.stats_payload)

    def seed_file(self, container_id: str, path: str, content: bytes) -> None:
        self.containers[container_id].filesystem[path] = content
