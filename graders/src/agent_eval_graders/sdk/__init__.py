"""Grader SDK — shared runtime for objective and future rubric graders."""

from __future__ import annotations

from agent_eval_graders.sdk.context import GradingConfig, GradingContext
from agent_eval_graders.sdk.exceptions import (
    DuplicateScoreError,
    GraderError,
    GraderInitializationError,
    GraderJudgmentError,
    GraderTimeoutError,
)
from agent_eval_graders.sdk.execution import (
    IsolatedGradingResult,
    run_grader,
    run_graders_isolated,
)
from agent_eval_graders.sdk.grader import BaseGrader, Grader
from agent_eval_graders.sdk.lifecycle import GraderPhase, LifecycleDriver
from agent_eval_graders.sdk.models import (
    GradingOutcome,
    GradingRunMetadata,
    ProducedScore,
)
from agent_eval_graders.sdk.ports import RunReader, ScoreSink
from agent_eval_graders.sdk.registry import GraderRegistry
from agent_eval_graders.sdk.result import (
    produce_objective_score,
    structured_detail,
)

__all__ = [
    "BaseGrader",
    "DuplicateScoreError",
    "Grader",
    "GraderError",
    "GraderInitializationError",
    "GraderJudgmentError",
    "GraderPhase",
    "GraderRegistry",
    "GraderTimeoutError",
    "GradingConfig",
    "GradingContext",
    "GradingOutcome",
    "GradingRunMetadata",
    "IsolatedGradingResult",
    "LifecycleDriver",
    "ProducedScore",
    "RunReader",
    "ScoreSink",
    "produce_objective_score",
    "run_grader",
    "run_graders_isolated",
    "structured_detail",
]
