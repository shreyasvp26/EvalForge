"""Judge provider abstraction + mock implementation (no vendor APIs)."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from agent_eval_graders.rubric.exceptions import JudgeProviderUnavailable, JudgeTimeout
from agent_eval_graders.rubric.models import JudgeRawResponse, JudgeRequest


@dataclass
class MockJudgeProvider:
    """Injectable mock judge — never calls an external LLM.

    Configure with a fixed response, a sequence of responses, or a callable.
    Can simulate timeouts and provider unavailability for failure tests.
    """

    response: str | None = None
    responses: Sequence[str] = ()
    handler: Callable[[JudgeRequest], JudgeRawResponse] | None = None
    model: str = "mock-judge"
    latency_ms: float = 1.0
    simulate_timeout: bool = False
    simulate_unavailable: bool = False
    sleep_seconds: float = 0.0
    _call_count: int = field(default=0, init=False, repr=False)

    def complete(self, request: JudgeRequest) -> JudgeRawResponse:
        self._call_count += 1
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)

        if self.simulate_timeout:
            raise JudgeTimeout(
                "Mock judge timed out",
                details={
                    "timeout_seconds": request.timeout_seconds,
                    "correlation_id": request.correlation_id,
                },
            )
        if self.simulate_unavailable:
            raise JudgeProviderUnavailable(
                "Mock judge provider unavailable",
                details={"correlation_id": request.correlation_id},
            )

        if self.handler is not None:
            return self.handler(request)

        content: str
        if self.responses:
            idx = min(self._call_count - 1, len(self.responses) - 1)
            content = self.responses[idx]
        elif self.response is not None:
            content = self.response
        else:
            content = (
                '{"numeric": 1.0, "passed": true, ' '"reason": "mock default pass"}'
            )

        return JudgeRawResponse(
            content=content,
            model=self.model,
            latency_ms=self.latency_ms,
            metadata={
                "temperature": request.controls.temperature,
                "seed": request.controls.seed,
                "model_hint": request.controls.model_hint,
            },
        )

    @property
    def call_count(self) -> int:
        return self._call_count
