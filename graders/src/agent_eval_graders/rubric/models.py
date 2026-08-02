"""Rubric grading value objects — immutable by construction."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RubricCriterion:
    """One criterion within an immutable rubric."""

    id: str
    description: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("RubricCriterion.id must be non-empty")
        if not self.description.strip():
            raise ValueError("RubricCriterion.description must be non-empty")
        if self.weight < 0:
            raise ValueError("RubricCriterion.weight must be >= 0")


@dataclass(frozen=True, slots=True)
class RubricSpecification:
    """Immutable rubric wording owned by a pinned Grader Version.

    Never mutate after construction. A wording change requires a new
    Grader Version (Grader Architecture — Versioning / Rubric Interpretation).
    """

    title: str
    instructions: str
    criteria: tuple[RubricCriterion, ...] = ()
    pass_threshold: float | None = None
    scale_min: float = 0.0
    scale_max: float = 1.0

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("RubricSpecification.title must be non-empty")
        if not self.instructions.strip():
            raise ValueError("RubricSpecification.instructions must be non-empty")
        if self.scale_min > self.scale_max:
            raise ValueError("scale_min must be <= scale_max")
        if self.pass_threshold is not None and not (
            self.scale_min <= self.pass_threshold <= self.scale_max
        ):
            raise ValueError("pass_threshold must lie within [scale_min, scale_max]")

    def fingerprint(self) -> str:
        """Stable hash of rubric wording — ties prompt to Grader Version content."""
        payload = {
            "title": self.title,
            "instructions": self.instructions,
            "criteria": [
                {"id": c.id, "description": c.description, "weight": c.weight}
                for c in self.criteria
            ],
            "pass_threshold": self.pass_threshold,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class DeterminismControls:
    """Controls that minimize judge variance (bounded, not bit-identical)."""

    temperature: float = 0.0
    max_tokens: int = 2048
    seed: int | None = 0
    model_hint: str = "mock-judge"


@dataclass(frozen=True, slots=True)
class JudgePrompt:
    """Prompt built solely from Run record + pinned rubric."""

    system: str
    user: str
    grader_version_id: str
    rubric_fingerprint: str


@dataclass(frozen=True, slots=True)
class JudgeRequest:
    prompt: JudgePrompt
    controls: DeterminismControls
    timeout_seconds: float
    correlation_id: str


@dataclass(frozen=True, slots=True)
class JudgeRawResponse:
    content: str
    model: str
    latency_ms: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CriterionScore:
    criterion_id: str
    score: float
    reason: str = ""
    passed: bool | None = None


@dataclass(frozen=True, slots=True)
class ParsedJudgment:
    """Strictly validated judge output ready for Score production."""

    numeric: float | None
    passed: bool | None
    reason: str
    criteria: tuple[CriterionScore, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    raw_content: str = ""

    def __post_init__(self) -> None:
        if self.numeric is None and self.passed is None:
            raise ValueError("ParsedJudgment requires numeric and/or passed")
        if not self.reason.strip():
            raise ValueError("ParsedJudgment.reason must be non-empty")
