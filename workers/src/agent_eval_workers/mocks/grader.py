"""Deterministic mock Graders — judgment stubs for orchestration tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId


@dataclass(frozen=True, slots=True)
class MockScore:
    """Deterministic Score payload produced by a MockGrader."""

    grader_id: str
    grader_version_id: str
    numeric: float | None = None
    categorical: str | None = None
    passed: bool | None = True


@dataclass(slots=True)
class MockGrader:
    """Isolated grader stub — failure never affects sibling graders."""

    grader_id: str
    grader_version_id: str
    numeric: float = 1.0
    passed: bool = True
    fail: bool = False
    invocations: list[RunId] = field(default_factory=list)

    def grade(self, run_id: RunId) -> MockScore | None:
        self.invocations.append(run_id)
        if self.fail:
            return None
        return MockScore(
            grader_id=self.grader_id,
            grader_version_id=self.grader_version_id,
            numeric=self.numeric,
            passed=self.passed,
        )
