"""Rubric grader runner — LLM-as-judge lifecycle over the shared Grader SDK."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.rubric.exceptions import (
    JudgeProviderUnavailable,
    JudgeTimeout,
    RubricError,
    RubricParseError,
    RubricPromptError,
)
from agent_eval_graders.rubric.judge import MockJudgeProvider
from agent_eval_graders.rubric.models import (
    DeterminismControls,
    JudgePrompt,
    JudgeRawResponse,
    JudgeRequest,
    ParsedJudgment,
    RubricSpecification,
)
from agent_eval_graders.rubric.ports import JudgeProvider, PromptBuilder, ResponseParser
from agent_eval_graders.rubric.prompt_builder import RubricPromptBuilder
from agent_eval_graders.rubric.response_parser import StrictResponseParser
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.exceptions import GraderError, GraderTimeoutError
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore, make_score
from agent_eval_graders.sdk.result import structured_detail


@dataclass
class JudgeRunner:
    """Invokes an injectable JudgeProvider with timeout / failure classification."""

    provider: JudgeProvider
    controls: DeterminismControls = field(default_factory=DeterminismControls)

    def invoke(
        self,
        *,
        prompt: JudgePrompt,
        context: GradingContext,
    ) -> JudgeRawResponse:
        context.check_timeout()
        request = JudgeRequest(
            prompt=prompt,
            controls=self.controls,
            timeout_seconds=context.config.timeout_seconds,
            correlation_id=context.correlation_id,
        )
        try:
            return self.provider.complete(request)
        except (JudgeTimeout, GraderTimeoutError):
            raise
        except JudgeProviderUnavailable:
            raise
        except GraderError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Unexpected provider exceptions → retryable infrastructure class.
            raise JudgeProviderUnavailable(
                f"Judge provider failed: {exc}",
                details={"correlation_id": context.correlation_id},
                cause=exc,
            ) from exc


@dataclass
class RubricGrader(BaseGrader):
    """Rubric / LLM-as-judge grading family.

    Implements the shared Grader contract. Internally runs:

        initialize → build_prompt → invoke_judge → parse_response
                   → produce_scores → cleanup

    Stateless across invocations. Rubric wording is immutable and owned by
    the pinned Grader Version (passed as ``rubric``).
    """

    rubric: RubricSpecification
    provider: JudgeProvider = field(default_factory=MockJudgeProvider)
    prompt_builder: PromptBuilder = field(default_factory=RubricPromptBuilder)
    response_parser: ResponseParser = field(default_factory=StrictResponseParser)
    controls: DeterminismControls = field(default_factory=DeterminismControls)
    name: str = "rubric"

    def __post_init__(self) -> None:
        # Freeze reference — callers must not mutate rubric after construction.
        object.__setattr__(self, "_rubric_fingerprint", self.rubric.fingerprint())

    def initialize(self, context: GradingContext) -> None:
        context.check_timeout()
        if not context.grader_version_id.value.strip():
            raise RubricPromptError("Pinned grader_version_id is required")
        current = self.rubric.fingerprint()
        expected = self._rubric_fingerprint
        if current != expected:
            raise RubricPromptError(
                "Rubric specification mutated after grader construction",
                details={"expected": expected, "got": current},
            )

    def build_prompt(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> JudgePrompt:
        return self.prompt_builder.build(
            context=context,
            events=events,
            artifacts=artifacts,
            rubric=self.rubric,
        )

    def invoke_judge(
        self,
        context: GradingContext,
        prompt: JudgePrompt,
    ) -> JudgeRawResponse:
        runner = JudgeRunner(provider=self.provider, controls=self.controls)
        return runner.invoke(prompt=prompt, context=context)

    def parse_response(
        self,
        raw: JudgeRawResponse,
    ) -> ParsedJudgment:
        return self.response_parser.parse(
            raw,
            rubric=self.rubric,
            controls=self.controls,
        )

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        """Shared Grader.grade — orchestrates rubric-specific phases."""
        context.check_timeout()
        try:
            prompt = self.build_prompt(context, events, artifacts)
            context.check_timeout()
            raw = self.invoke_judge(context, prompt)
            context.check_timeout()
            judgment = self.parse_response(raw)
            return {
                "judgment": judgment,
                "prompt": prompt,
                "raw": raw,
            }
        except (JudgeTimeout, GraderTimeoutError):
            raise
        except JudgeProviderUnavailable:
            raise
        except (RubricParseError, RubricPromptError, RubricError):
            raise
        except GraderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RubricError(
                f"Rubric grading failed: {exc}",
                details={
                    "grader_id": context.grader_id.value,
                    "grader_version_id": context.grader_version_id.value,
                },
                cause=exc,
            ) from exc

    def produce_scores(
        self,
        context: GradingContext,
        judgment: object,
    ) -> Sequence[ProducedScore]:
        data = judgment if isinstance(judgment, dict) else {}
        parsed = data.get("judgment")
        if not isinstance(parsed, ParsedJudgment):
            raise RubricParseError(
                "produce_scores expected ParsedJudgment from grade()",
                details={"got": type(parsed).__name__},
            )

        prompt = data.get("prompt")
        fingerprint = (
            prompt.rubric_fingerprint
            if isinstance(prompt, JudgePrompt)
            else self.rubric.fingerprint()
        )

        criteria_detail = [
            {
                "criterion_id": c.criterion_id,
                "name": c.criterion_id,
                "score": c.score,
                "reason": c.reason,
                "passed": c.passed,
            }
            for c in parsed.criteria
        ]
        score_value = parsed.numeric
        if score_value is None and parsed.passed is not None:
            score_value = 1.0 if parsed.passed else 0.0
        return (
            make_score(
                score_id=ScoreId(f"score-{uuid4().hex[:12]}"),
                run_id=context.reader.metadata().run_id,
                grader_id=context.grader_id,
                grader_version_id=context.grader_version_id,
                passed=parsed.passed,
                numeric=parsed.numeric,
                reason=parsed.reason,
                detail=structured_detail(
                    grader=self.name,
                    family="rubric",
                    passed=parsed.passed,
                    score=score_value,
                    max_score=self.rubric.scale_max,
                    reason=parsed.reason,
                    evidence={"criteria": criteria_detail},
                    metadata={
                        "rubric_fingerprint": fingerprint,
                        "judge_metadata": dict(parsed.metadata),
                        "determinism": {
                            "temperature": self.controls.temperature,
                            "seed": self.controls.seed,
                            "model_hint": self.controls.model_hint,
                        },
                    },
                    criteria=criteria_detail,
                    rubric_fingerprint=fingerprint,
                    judge_metadata=dict(parsed.metadata),
                    determinism={
                        "temperature": self.controls.temperature,
                        "seed": self.controls.seed,
                        "model_hint": self.controls.model_hint,
                    },
                ),
                metadata={
                    "family": "rubric",
                    "rubric_fingerprint": fingerprint,
                    "grader_version_label": context.grader_version_label,
                },
            ),
        )

    def cleanup(self, context: GradingContext) -> None:
        del context
