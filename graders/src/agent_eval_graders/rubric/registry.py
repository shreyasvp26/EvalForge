"""Rubric grader registry helpers."""

from __future__ import annotations

from agent_eval_graders.rubric.models import RubricSpecification
from agent_eval_graders.rubric.ports import JudgeProvider
from agent_eval_graders.rubric.runner import RubricGrader
from agent_eval_graders.sdk.registry import GraderRegistry


def register_rubric_graders(registry: GraderRegistry) -> GraderRegistry:
    """Register the rubric grading family on ``registry``.

    Factory requires ``rubric=`` (and optionally ``provider=``) at create time.
    """
    registry.register("rubric", RubricGrader)
    return registry


def create_rubric_grader(
    *,
    rubric: RubricSpecification,
    provider: JudgeProvider | None = None,
    name: str = "rubric",
) -> RubricGrader:
    """Convenience factory for a fresh, stateless RubricGrader."""
    kwargs: dict[str, object] = {"rubric": rubric, "name": name}
    if provider is not None:
        kwargs["provider"] = provider
    return RubricGrader(**kwargs)  # type: ignore[arg-type]


def default_rubric_registry() -> GraderRegistry:
    return register_rubric_graders(GraderRegistry())
