"""Materialize a Case Version's reference repository into a Sandbox workspace.

Clone/fetch the repository, check out the exact commit SHA, and verify HEAD
matches before the coding-agent adapter starts. Never evaluates a branch tip
when a commit is pinned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListCasesByProjectQuery
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest, SandboxHandle
from agent_eval_shared.log import get_logger

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause

logger = get_logger(__name__)

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


class RepositoryMaterializationError(RuntimeError):
    """Repository could not be materialized at the pinned revision."""


@dataclass(frozen=True, slots=True)
class ReferenceRepository:
    repository_url: str
    commit_sha: str
    subdirectory: str | None = None


@dataclass(slots=True)
class CaseReferenceResolver:
    """Load ``ReferenceRepositoryState`` for the Run's pinned Case Version."""

    actor: Actor
    get_run: object
    list_cases: object

    def resolve(self, run_id: RunId) -> ReferenceRepository:
        run = self.get_run.execute(  # type: ignore[attr-defined]
            GetRunQuery(actor=self.actor, run_id=run_id.value)
        )
        case_version_id = run.pins.case_version_id
        cases = self.list_cases.execute(  # type: ignore[attr-defined]
            ListCasesByProjectQuery(actor=self.actor, project_id=run.pins.project_id)
        )
        for case in cases:
            for version in case.versions:
                if version.id == case_version_id:
                    url = str(version.repository_url).strip()
                    sha = str(version.commit_sha).strip()
                    sub = version.subdirectory
                    subdirectory = str(sub).strip() if sub else None
                    if not url:
                        raise RepositoryMaterializationError(
                            f"Case version {case_version_id} has empty repository_url"
                        )
                    if not sha or not _SHA_RE.match(sha):
                        raise RepositoryMaterializationError(
                            f"Case version {case_version_id} has invalid commit_sha "
                            f"{sha!r}; expected a 7–40 character hex SHA"
                        )
                    return ReferenceRepository(
                        repository_url=url,
                        commit_sha=sha,
                        subdirectory=subdirectory or None,
                    )
        raise RepositoryMaterializationError(
            f"Pinned case version {case_version_id!r} not found in project catalog"
        )


@dataclass(slots=True)
class RepositoryMaterializer:
    """Clone and check out an exact revision inside an already-started sandbox."""

    manager: SandboxManager
    working_directory: str = "/workspace"
    clone_timeout_seconds: float = 120.0
    command_timeout_seconds: float = 60.0

    def materialize(
        self,
        handle: SandboxHandle,
        reference: ReferenceRepository,
    ) -> str:
        """Materialize ``reference`` into the sandbox; return workspace path.

        Returns the adapter working directory (``/workspace`` or subdirectory).
        """
        url = reference.repository_url
        sha = reference.commit_sha
        # Never log credentials — URLs must not embed tokens.
        safe_url = _redact_url(url)
        logger.info(
            "repository_materialize_start",
            repository_url=safe_url,
            commit_sha=sha,
            subdirectory=reference.subdirectory,
        )

        self._exec(
            handle,
            (
                "sh",
                "-c",
                f"rm -rf {self.working_directory}/.git "
                f"{self.working_directory}/* "
                f"{self.working_directory}/.[!.]* 2>/dev/null || true",
            ),
            timeout=self.command_timeout_seconds,
            allow_nonzero=True,
        )
        # Initialize and fetch the exact commit (works for public repos with bridge).
        self._exec(
            handle,
            ("git", "init", self.working_directory),
            timeout=self.command_timeout_seconds,
        )
        self._exec(
            handle,
            ("git", "-C", self.working_directory, "remote", "add", "origin", url),
            timeout=self.command_timeout_seconds,
        )
        fetch = self._exec(
            handle,
            (
                "git",
                "-C",
                self.working_directory,
                "fetch",
                "--depth",
                "1",
                "origin",
                sha,
            ),
            timeout=self.clone_timeout_seconds,
            allow_nonzero=True,
        )
        if fetch.exit_code != 0:
            # Fallback: full fetch when shallow fetch of a SHA is unsupported.
            self._exec(
                handle,
                ("git", "-C", self.working_directory, "fetch", "origin"),
                timeout=self.clone_timeout_seconds,
            )
        self._exec(
            handle,
            ("git", "-C", self.working_directory, "checkout", "--detach", sha),
            timeout=self.command_timeout_seconds,
        )
        head = self._exec(
            handle,
            ("git", "-C", self.working_directory, "rev-parse", "HEAD"),
            timeout=self.command_timeout_seconds,
        )
        actual = head.stdout.strip()
        if not _sha_matches(requested=sha, actual=actual):
            raise RepositoryMaterializationError(
                f"Checked-out HEAD {actual!r} does not match pinned commit {sha!r} "
                f"for repository {safe_url}"
            )

        workspace = self.working_directory
        if reference.subdirectory:
            base = self.working_directory.rstrip("/")
            sub = reference.subdirectory.strip("/")
            workspace = f"{base}/{sub}"
            listed = self._exec(
                handle,
                ("test", "-d", workspace),
                timeout=self.command_timeout_seconds,
                allow_nonzero=True,
            )
            if listed.exit_code != 0:
                raise RepositoryMaterializationError(
                    f"Pinned subdirectory {reference.subdirectory!r} does not exist "
                    f"at commit {sha} in {safe_url}"
                )

        logger.info(
            "repository_materialize_ok",
            repository_url=safe_url,
            commit_sha=sha,
            head=actual,
            workspace=workspace,
        )
        return workspace

    def _exec(
        self,
        handle: SandboxHandle,
        command: tuple[str, ...],
        *,
        timeout: float,
        allow_nonzero: bool = False,
    ):
        result = self.manager.execute(
            handle,
            ExecutionRequest(command=command, timeout_seconds=timeout),
        )
        if result.timed_out:
            raise RepositoryMaterializationError(
                f"Repository command timed out: {_safe_command(command)}"
            )
        if result.exit_code != 0 and not allow_nonzero:
            stderr = (result.stderr or "").strip()
            raise RepositoryMaterializationError(
                f"Repository command failed ({result.exit_code}): "
                f"{_safe_command(command)}" + (f" — {stderr}" if stderr else "")
            )
        return result


@dataclass
class SandboxRepositoryPreparer:
    """``after_provision`` hook: resolve case repo + materialize into sandbox."""

    actor: Actor
    get_run: object
    list_cases: object
    manager: SandboxManager
    sandboxes: RunSandboxRegistry
    materializer: RepositoryMaterializer | None = None
    # Per-run working directories for the adapter (subdirectory-aware).
    workspaces: dict[str, str] = field(default_factory=dict)
    _resolver: CaseReferenceResolver | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        if self.materializer is None:
            self.materializer = RepositoryMaterializer(manager=self.manager)
        self._resolver = CaseReferenceResolver(
            actor=self.actor,
            get_run=self.get_run,
            list_cases=self.list_cases,
        )

    def __call__(self, run_id: RunId) -> None:
        try:
            assert self._resolver is not None
            reference = self._resolver.resolve(run_id)
            handle = self.sandboxes.get(run_id)
            assert self.materializer is not None
            workspace = self.materializer.materialize(handle, reference)
            self.workspaces[run_id.value] = workspace
        except RepositoryMaterializationError as exc:
            raise RecoverableExecutionError(
                str(exc),
                cause=FailureCause.REPOSITORY_PREPARATION,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RecoverableExecutionError(
                f"Repository materialization failed for {run_id.value}: {exc}",
                cause=FailureCause.REPOSITORY_PREPARATION,
            ) from exc


def _sha_matches(*, requested: str, actual: str) -> bool:
    req = requested.lower()
    act = actual.lower()
    if req == act:
        return True
    # Allow abbreviated pins when HEAD is the full SHA.
    return len(req) >= 7 and act.startswith(req)


def _redact_url(url: str) -> str:
    # Strip userinfo (https://token@host/...) without logging secrets.
    return re.sub(r"://[^/@]+@", "://***@", url)


def _safe_command(command: tuple[str, ...]) -> str:
    redacted: list[str] = []
    for part in command:
        if "://" in part and "@" in part:
            redacted.append(_redact_url(part))
        else:
            redacted.append(part)
    return " ".join(redacted)
