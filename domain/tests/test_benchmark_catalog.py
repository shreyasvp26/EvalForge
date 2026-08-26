"""Domain tests for benchmark catalog foundations."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import CaseId, ProjectId, PromptId, SuiteId
from agent_eval_domain.evaluation_management.case import (
    EvaluationCase,
    ReferenceRepositoryState,
)
from agent_eval_domain.evaluation_management.suite import EvaluationSuite


def test_reference_repository_rejects_branch_names() -> None:
    with pytest.raises(InvariantViolation) as exc:
        ReferenceRepositoryState(
            repository_url="https://github.com/example/repo.git",
            commit_sha="main",
        )
    assert exc.value.code == "BRANCH_REVISION_FORBIDDEN"


def test_reference_repository_requires_hex_sha() -> None:
    with pytest.raises(InvariantViolation) as exc:
        ReferenceRepositoryState(
            repository_url="https://github.com/example/repo.git",
            commit_sha="not-a-sha",
        )
    assert exc.value.code == "INVALID_REFERENCE_COMMIT"


def test_suite_catalog_fields() -> None:
    suite = EvaluationSuite.create(
        suite_id=SuiteId("suite-1"),
        project_id=ProjectId("proj-1"),
        name="EvalForge Coding Benchmark",
        catalog_key="coding-benchmark-v1",
        catalog_visible=True,
    )
    assert suite.catalog_key == "coding-benchmark-v1"
    assert suite.catalog_visible is True
    suite.set_catalog(catalog_visible=False)
    assert suite.catalog_visible is False


def test_case_catalog_metadata() -> None:
    case = EvaluationCase.create(
        case_id=CaseId("case-1"),
        project_id=ProjectId("proj-1"),
        prompt_id=PromptId("prompt-1"),
        name="Fix arithmetic bug",
        category="bugfix",
        difficulty="easy",
        language="python",
        tags=("pytest", "arithmetic"),
    )
    assert case.category == "bugfix"
    assert case.difficulty == "easy"
    assert case.language == "python"
    assert case.tags == ("pytest", "arithmetic")
