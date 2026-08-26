"""Run publication state — GitHub branch/PR after evaluation PASS.

Publication is intentionally separate from RunStatus and FailureCategory.
A completed evaluation with passing scores may still fail to publish; that
must not rewrite the evaluation outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now


class PublicationStatus(StrEnum):
    """Lifecycle of post-evaluation GitHub publication for one Run."""

    NOT_ATTEMPTED = "not_attempted"
    SKIPPED = "skipped"
    """Evaluation did not pass (or was ineligible); no branch/PR."""

    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"
    FAILED = "failed"
    """GitHub publication failed; evaluation result remains intact."""


_ALLOWED_PUBLICATION_KEYS = frozenset(
    {
        "status",
        "branch_name",
        "base_commit_sha",
        "result_commit_sha",
        "pull_request_url",
        "pull_request_number",
        "repository_url",
        "error_code",
        "error_message",
        "attempted_at",
        "published_at",
        "idempotency_key",
    }
)


def publication_branch_name(*, case_id: str, run_id: str) -> str:
    """Deterministic, attributable branch name anchored on run identity."""
    case = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in case_id.strip())
    run = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in run_id.strip())
    if not case or not run:
        raise InvariantViolation(
            "case_id and run_id are required for publication branch naming",
            code="INVALID_PUBLICATION_BRANCH",
        )
    # Keep under GitHub's practical ref length while remaining unique per run.
    name = f"evalforge/task-{case[:48]}-run-{run[:48]}"
    return name[:200]


@dataclass(frozen=True, slots=True)
class RunPublication:
    """Non-secret GitHub publication projection for a Run."""

    status: PublicationStatus = PublicationStatus.NOT_ATTEMPTED
    branch_name: str | None = None
    base_commit_sha: str | None = None
    result_commit_sha: str | None = None
    pull_request_url: str | None = None
    pull_request_number: int | None = None
    repository_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempted_at: datetime | None = None
    published_at: datetime | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, PublicationStatus):
            object.__setattr__(
                self, "status", PublicationStatus(str(self.status).strip())
            )
        for field_name in (
            "branch_name",
            "base_commit_sha",
            "result_commit_sha",
            "pull_request_url",
            "repository_url",
            "error_code",
            "error_message",
            "idempotency_key",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            cleaned = str(value).strip()
            object.__setattr__(self, field_name, cleaned or None)
        if self.pull_request_number is not None:
            number = int(self.pull_request_number)
            if number <= 0:
                raise InvariantViolation(
                    "pull_request_number must be positive when set",
                    code="INVALID_PUBLICATION_PR_NUMBER",
                )
            object.__setattr__(self, "pull_request_number", number)

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            PublicationStatus.SKIPPED,
            PublicationStatus.PUBLISHED,
            PublicationStatus.FAILED,
        }

    @property
    def is_published(self) -> bool:
        return self.status is PublicationStatus.PUBLISHED

    def to_public_dict(self) -> dict[str, object]:
        """API/provenance-safe projection (never includes secrets)."""
        payload: dict[str, object] = {"status": self.status.value}
        if self.branch_name:
            payload["branch_name"] = self.branch_name
        if self.base_commit_sha:
            payload["base_commit_sha"] = self.base_commit_sha
        if self.result_commit_sha:
            payload["result_commit_sha"] = self.result_commit_sha
        if self.pull_request_url:
            payload["pull_request_url"] = self.pull_request_url
        if self.pull_request_number is not None:
            payload["pull_request_number"] = self.pull_request_number
        if self.repository_url:
            payload["repository_url"] = self.repository_url
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.error_message:
            # Defensive redaction for accidental token fragments in messages.
            message = self.error_message
            lowered = message.lower()
            if any(
                marker in lowered
                for marker in ("sk-", "ghp_", "github_pat_", "bearer ", "api_key=")
            ):
                message = "publication failed (details redacted)"
            payload["error_message"] = message
        if self.attempted_at is not None:
            payload["attempted_at"] = self.attempted_at.isoformat()
        if self.published_at is not None:
            payload["published_at"] = self.published_at.isoformat()
        if self.idempotency_key:
            payload["idempotency_key"] = self.idempotency_key
        return payload

    @classmethod
    def from_mapping(cls, raw: dict[str, object] | None) -> RunPublication:
        if not raw:
            return cls()
        cleaned = {
            key: value
            for key, value in raw.items()
            if key in _ALLOWED_PUBLICATION_KEYS and value is not None
        }
        status_raw = cleaned.get("status", PublicationStatus.NOT_ATTEMPTED.value)
        attempted = cleaned.get("attempted_at")
        published = cleaned.get("published_at")
        return cls(
            status=PublicationStatus(str(status_raw)),
            branch_name=_optional_str(cleaned.get("branch_name")),
            base_commit_sha=_optional_str(cleaned.get("base_commit_sha")),
            result_commit_sha=_optional_str(cleaned.get("result_commit_sha")),
            pull_request_url=_optional_str(cleaned.get("pull_request_url")),
            pull_request_number=_optional_int(cleaned.get("pull_request_number")),
            repository_url=_optional_str(cleaned.get("repository_url")),
            error_code=_optional_str(cleaned.get("error_code")),
            error_message=_optional_str(cleaned.get("error_message")),
            attempted_at=_optional_dt(attempted),
            published_at=_optional_dt(published),
            idempotency_key=_optional_str(cleaned.get("idempotency_key")),
        )

    def mark_skipped(self, *, reason: str) -> RunPublication:
        return RunPublication(
            status=PublicationStatus.SKIPPED,
            branch_name=self.branch_name,
            base_commit_sha=self.base_commit_sha,
            repository_url=self.repository_url,
            error_code="EVALUATION_NOT_PASSED",
            error_message=reason,
            attempted_at=utc_now(),
            idempotency_key=self.idempotency_key,
        )

    def mark_in_progress(
        self,
        *,
        branch_name: str,
        base_commit_sha: str,
        repository_url: str,
        idempotency_key: str,
    ) -> RunPublication:
        return RunPublication(
            status=PublicationStatus.IN_PROGRESS,
            branch_name=branch_name,
            base_commit_sha=base_commit_sha,
            repository_url=repository_url,
            attempted_at=utc_now(),
            idempotency_key=idempotency_key,
        )

    def mark_published(
        self,
        *,
        result_commit_sha: str,
        pull_request_url: str,
        pull_request_number: int,
    ) -> RunPublication:
        if self.status is not PublicationStatus.IN_PROGRESS and not self.is_published:
            # Allow idempotent completion from in-progress or already-published.
            pass
        return RunPublication(
            status=PublicationStatus.PUBLISHED,
            branch_name=self.branch_name,
            base_commit_sha=self.base_commit_sha,
            result_commit_sha=result_commit_sha,
            pull_request_url=pull_request_url,
            pull_request_number=pull_request_number,
            repository_url=self.repository_url,
            attempted_at=self.attempted_at or utc_now(),
            published_at=utc_now(),
            idempotency_key=self.idempotency_key,
        )

    def mark_failed(self, *, error_code: str, error_message: str) -> RunPublication:
        return RunPublication(
            status=PublicationStatus.FAILED,
            branch_name=self.branch_name,
            base_commit_sha=self.base_commit_sha,
            result_commit_sha=self.result_commit_sha,
            pull_request_url=self.pull_request_url,
            pull_request_number=self.pull_request_number,
            repository_url=self.repository_url,
            error_code=error_code,
            error_message=error_message,
            attempted_at=self.attempted_at or utc_now(),
            idempotency_key=self.idempotency_key,
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_dt(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)
