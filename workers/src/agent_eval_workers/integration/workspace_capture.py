"""Capture workspace file changes from a live sandbox for GitHub publication."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_application.ports.github_publication import WorkspaceFileChange
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest, ExecutionResult, SandboxHandle

from agent_eval_workers.integration.registry import RunSandboxRegistry

WorkingDirFactory = Callable[[RunId], str]


@dataclass(slots=True)
class SandboxWorkspaceCapture:
    """Read git-tracked and untracked changes relative to HEAD / base."""

    manager: SandboxManager
    sandboxes: RunSandboxRegistry
    working_directory_factory: WorkingDirFactory

    def capture_changes(
        self,
        run_id: RunId,
        *,
        base_commit_sha: str | None = None,
    ) -> tuple[WorkspaceFileChange, ...]:
        handle = self.sandboxes.get(run_id)
        if handle is None:
            return ()
        workdir = self.working_directory_factory(run_id)
        status = self._exec(
            handle,
            workdir,
            ("git", "status", "--porcelain", "-uall"),
        )
        if status.exit_code != 0:
            return ()
        paths: list[tuple[str, str]] = []
        for line in status.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1].strip()
            if not path or path.startswith(".git"):
                continue
            if code.strip() == "D" or code.endswith("D"):
                paths.append((path, "deleted"))
            elif code.strip().startswith("?"):
                paths.append((path, "added"))
            else:
                paths.append((path, "modified"))

        if not paths and base_commit_sha:
            diff_names = self._exec(
                handle,
                workdir,
                ("git", "diff", "--name-status", base_commit_sha),
            )
            if diff_names.exit_code == 0:
                for line in diff_names.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) < 2:
                        continue
                    status_code, path = parts[0], parts[-1]
                    if status_code.startswith("D"):
                        paths.append((path, "deleted"))
                    elif status_code.startswith("A"):
                        paths.append((path, "added"))
                    else:
                        paths.append((path, "modified"))

        changes: list[WorkspaceFileChange] = []
        for path, status_name in paths:
            if status_name == "deleted":
                changes.append(
                    WorkspaceFileChange(path=path, content=None, status="deleted")
                )
                continue
            content = self._read_file(handle, workdir, path)
            if content is None:
                continue
            changes.append(
                WorkspaceFileChange(path=path, content=content, status=status_name)
            )
        return tuple(changes)

    def capture_unified_diff(
        self, run_id: RunId, *, base_commit_sha: str | None = None
    ) -> str:
        handle = self.sandboxes.get(run_id)
        if handle is None:
            return ""
        workdir = self.working_directory_factory(run_id)
        args: tuple[str, ...] = ("git", "diff")
        if base_commit_sha:
            args = ("git", "diff", base_commit_sha)
        result = self._exec(handle, workdir, args)
        if result.exit_code != 0:
            return ""
        return result.stdout

    def _exec(
        self,
        handle: SandboxHandle,
        workdir: str,
        command: tuple[str, ...],
    ) -> ExecutionResult:
        return self.manager.execute(
            handle,
            ExecutionRequest(
                command=command,
                working_dir=workdir,
                timeout_seconds=60.0,
            ),
        )

    def _read_file(
        self, handle: SandboxHandle, workdir: str, path: str
    ) -> bytes | None:
        container_path = (
            path if path.startswith("/") else f"{workdir.rstrip('/')}/{path}"
        )
        result = self._exec(handle, workdir, ("cat", container_path))
        if result.exit_code != 0:
            return None
        return result.stdout.encode("utf-8")
