"""Strict judge response parsing — malformed → GradingFailure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_eval_graders.rubric.exceptions import RubricParseError, RubricSchemaError
from agent_eval_graders.rubric.models import (
    CriterionScore,
    DeterminismControls,
    JudgeRawResponse,
    ParsedJudgment,
    RubricSpecification,
)


@dataclass(frozen=True, slots=True)
class StrictResponseParser:
    """Validate judge JSON against a strict schema.

    Malformed JSON or schema mismatches become judgment failures
    (not retryable). Partial / missing required fields fail closed.
    """

    require_criteria_when_defined: bool = False

    def parse(
        self,
        raw: JudgeRawResponse,
        *,
        rubric: RubricSpecification,
        controls: DeterminismControls,
    ) -> ParsedJudgment:
        del controls  # reserved for future model-specific validation
        text = (raw.content or "").strip()
        if not text:
            raise RubricParseError(
                "Judge response was empty",
                details={"model": raw.model},
            )

        # Strip accidental markdown fences without accepting free-form prose.
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RubricParseError(
                f"Judge response is not valid JSON: {exc}",
                details={"model": raw.model, "content_preview": text[:200]},
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise RubricSchemaError(
                "Judge response JSON root must be an object",
                details={"type": type(payload).__name__},
            )

        numeric = self._optional_float(payload, "numeric")
        if numeric is None:
            # Accept Phase 6 conceptual shape: {"score": 0.85, ...}
            numeric = self._optional_float(payload, "score")
        passed = self._optional_bool(payload, "passed")
        if numeric is None and passed is None:
            raise RubricSchemaError(
                "Judge response must include numeric/score and/or passed",
                details={"keys": sorted(payload.keys())},
            )

        reason = payload.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise RubricSchemaError(
                "Judge response reason must be a non-empty string",
            )

        if numeric is not None and not (
            rubric.scale_min <= numeric <= rubric.scale_max
        ):
            raise RubricSchemaError(
                "Judge numeric score outside rubric scale",
                details={
                    "numeric": numeric,
                    "scale_min": rubric.scale_min,
                    "scale_max": rubric.scale_max,
                },
            )

        # Derive passed from threshold when judge omitted it.
        if passed is None and numeric is not None and rubric.pass_threshold is not None:
            passed = numeric >= rubric.pass_threshold

        criteria = self._parse_criteria(payload.get("criteria"), rubric=rubric)
        if self.require_criteria_when_defined and rubric.criteria and not criteria:
            raise RubricSchemaError(
                "Judge response missing required criteria breakdown",
                details={"expected": [c.id for c in rubric.criteria]},
            )

        metadata = payload.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise RubricSchemaError("Judge response metadata must be an object")
        # Ensure JSON-serializable string keys only.
        clean_meta: dict[str, Any] = {}
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise RubricSchemaError("metadata keys must be strings")
            clean_meta[key] = value

        clean_meta.setdefault("judge_model", raw.model)
        if raw.latency_ms is not None:
            clean_meta.setdefault("judge_latency_ms", raw.latency_ms)

        return ParsedJudgment(
            numeric=numeric,
            passed=passed,
            reason=reason.strip(),
            criteria=tuple(criteria),
            metadata=clean_meta,
            raw_content=raw.content,
        )

    def _parse_criteria(
        self,
        raw_criteria: object,
        *,
        rubric: RubricSpecification,
    ) -> list[CriterionScore]:
        if raw_criteria is None:
            return []
        if not isinstance(raw_criteria, list):
            raise RubricSchemaError("criteria must be an array")

        known = {c.id for c in rubric.criteria}
        parsed: list[CriterionScore] = []
        seen: set[str] = set()
        for item in raw_criteria:
            if not isinstance(item, dict):
                raise RubricSchemaError("each criteria entry must be an object")
            cid = item.get("criterion_id") or item.get("name") or item.get("id")
            if not isinstance(cid, str) or not cid.strip():
                raise RubricSchemaError(
                    "criterion_id (or name/id) must be a non-empty string"
                )
            if known and cid not in known:
                raise RubricSchemaError(
                    f"Unknown criterion_id {cid!r}",
                    details={"known": sorted(known)},
                )
            if cid in seen:
                raise RubricSchemaError(
                    f"Duplicate criterion_id {cid!r}",
                )
            seen.add(cid)
            score = self._required_float(item, "score")
            reason = item.get("reason", "")
            if reason is None:
                reason = ""
            if not isinstance(reason, str):
                raise RubricSchemaError("criteria.reason must be a string")
            c_passed = self._optional_bool(item, "passed")
            parsed.append(
                CriterionScore(
                    criterion_id=cid,
                    score=score,
                    reason=reason,
                    passed=c_passed,
                )
            )
        return parsed

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RubricSchemaError(f"{key} must be a number")
        return float(value)

    @staticmethod
    def _required_float(payload: dict[str, Any], key: str) -> float:
        value = StrictResponseParser._optional_float(payload, key)
        if value is None:
            raise RubricSchemaError(f"{key} is required")
        return value

    @staticmethod
    def _optional_bool(payload: dict[str, Any], key: str) -> bool | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if not isinstance(value, bool):
            raise RubricSchemaError(f"{key} must be a boolean")
        return value
