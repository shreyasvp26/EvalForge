"""Production Docker engine adapter around ``docker.DockerClient``."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any

from agent_eval_sandbox.exceptions import SandboxExecutionError, SandboxTimeoutError


@dataclass(slots=True)
class DockerPyEngine:
    """``DockerEngine`` implementation using the official Docker SDK."""

    client: Any

    @classmethod
    def from_env(cls) -> DockerPyEngine:
        import docker

        return cls(client=docker.from_env())

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
        api = self.client.api
        # network_mode belongs on HostConfig, not create_container kwargs.
        host_config_payload = dict(host_config)
        if network_mode is not None:
            host_config_payload["NetworkMode"] = network_mode
        host_cfg = api.create_host_config(**_host_config_kwargs(host_config_payload))
        kwargs: dict[str, Any] = {
            "image": image,
            "command": command,
            "working_dir": working_dir,
            "environment": dict(environment),
            "labels": dict(labels),
            "host_config": host_cfg,
            "detach": True,
            "tty": False,
        }
        if name is not None:
            kwargs["name"] = name
        if networking_config is not None:
            endpoints = networking_config.get("EndpointsConfig", {})
            kwargs["networking_config"] = api.create_networking_config(
                {
                    net: api.create_endpoint_config()
                    for net in endpoints  # type: ignore[union-attr]
                }
            )
        created = api.create_container(**kwargs)
        return str(created["Id"])

    def start_container(self, container_id: str) -> None:
        self.client.api.start(container_id)

    def stop_container(self, container_id: str, *, timeout: float) -> None:
        self.client.api.stop(container_id, timeout=int(max(1, timeout)))

    def remove_container(self, container_id: str, *, force: bool = True) -> None:
        self.client.api.remove_container(container_id, force=force)

    def exec_run(
        self,
        container_id: str,
        *,
        command: list[str],
        working_dir: str | None,
        environment: Mapping[str, str] | None,
        timeout_seconds: float | None,
    ) -> tuple[int, bytes, bytes, bool]:
        """Execute ``command`` with in-container + host-side timeout enforcement."""
        container = self.client.containers.get(container_id)
        wrapped = _wrap_with_timeout(command, timeout_seconds)
        host_timeout = None if timeout_seconds is None else float(timeout_seconds) + 2.0

        def _run() -> tuple[int, bytes, bytes]:
            exit_code, output = container.exec_run(
                cmd=wrapped,
                workdir=working_dir,
                environment=dict(environment) if environment else None,
                demux=True,
            )
            stdout, stderr = _split_output(output)
            return int(exit_code), stdout, stderr

        try:
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(_run)
                exit_code, stdout, stderr = future.result(timeout=host_timeout)
            finally:
                # Never block forever on a stuck docker-py exec thread.
                pool.shutdown(wait=False, cancel_futures=True)
        except FuturesTimeoutError as exc:
            raise SandboxTimeoutError(
                f"Sandbox exec exceeded timeout of {timeout_seconds}s",
                details={
                    "container_id": container_id,
                    "timeout_seconds": timeout_seconds,
                },
                cause=exc,
            ) from exc
        except SandboxTimeoutError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SandboxExecutionError(
                f"Sandbox exec failed: {exc}",
                details={"container_id": container_id, "command": command},
                cause=exc,
            ) from exc

        # GNU coreutils ``timeout`` exits 124 on expiry; BusyBox ``timeout -s KILL``
        # typically surfaces 128+9=137 when the wrapped command is killed.
        timed_out = timeout_seconds is not None and exit_code in {124, 137}
        return exit_code, stdout, stderr, timed_out

    def get_archive(self, container_id: str, path: str) -> bytes:
        bits, _stat = self.client.containers.get(container_id).get_archive(path)
        return b"".join(bits)

    def container_stats(self, container_id: str) -> Mapping[str, object]:
        return dict(self.client.containers.get(container_id).stats(stream=False))


def _wrap_with_timeout(
    command: list[str],
    timeout_seconds: float | None,
) -> list[str]:
    if timeout_seconds is None:
        return command
    # Portable across GNU coreutils and BusyBox (CI uses busybox:1.36).
    # Avoid GNU-only ``--signal=KILL`` / ``15s`` duration forms.
    # Exit 124 on expiry is still the conventional timeout status.
    seconds = max(1, int(timeout_seconds))
    return ["timeout", "-s", "KILL", str(seconds), *command]


def _split_output(output: Any) -> tuple[bytes, bytes]:
    if output is None:
        return b"", b""
    if isinstance(output, tuple):
        out, err = output
        return out or b"", err or b""
    if isinstance(output, (bytes, bytearray)):
        return bytes(output), b""
    return b"", b""


def _host_config_kwargs(host_config: Mapping[str, object]) -> dict[str, Any]:
    mapping = {
        "NanoCpus": "nano_cpus",
        "Memory": "mem_limit",
        "MemorySwap": "memswap_limit",
        "PidsLimit": "pids_limit",
        "StorageOpt": "storage_opt",
        "Mounts": "mounts",
        "Dns": "dns",
        "NetworkMode": "network_mode",
    }
    kwargs: dict[str, Any] = {}
    for key, value in host_config.items():
        mapped = mapping.get(str(key), str(key))
        if key == "Mounts" and isinstance(value, list):
            kwargs[mapped] = [_to_docker_mount(m) for m in value]
        else:
            kwargs[mapped] = value
    return kwargs


def _to_docker_mount(mount: dict[str, Any]) -> dict[str, Any]:
    return {
        "Type": mount.get("Type", "bind"),
        "Source": mount["Source"],
        "Target": mount["Target"],
        "ReadOnly": bool(mount.get("ReadOnly", False)),
    }
