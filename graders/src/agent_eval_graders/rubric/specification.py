"""Parse GraderVersion.specification into an immutable RubricSpecification."""

from __future__ import annotations

import json
from typing import Any

from agent_eval_graders.rubric.models import RubricCriterion, RubricSpecification


def parse_rubric_specification(
    raw: str,
    *,
    default_title: str = "Rubric",
) -> RubricSpecification:
    """Parse pinned grader specification text into a RubricSpecification.

    Accepts:
    - JSON object with title/instructions/criteria/pass_threshold/scale_*
    - Free-form instructions (title defaults to ``default_title``)

    Invalid JSON objects (wrong types) raise ``ValueError`` so resolution
    fails closed rather than inventing a silent default rubric.
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError(
            "Rubric grader specification is empty; "
            "provide JSON rubric content or free-form instructions"
        )

    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Rubric grader specification is not valid JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError("Rubric JSON specification root must be an object")
        return _from_mapping(payload, default_title=default_title)

    return RubricSpecification(
        title=default_title.strip() or "Rubric",
        instructions=text,
        criteria=(),
        pass_threshold=0.5,
        scale_min=0.0,
        scale_max=1.0,
    )


def _from_mapping(
    payload: dict[str, Any],
    *,
    default_title: str,
) -> RubricSpecification:
    title = payload.get("title")
    if title is None or (isinstance(title, str) and not title.strip()):
        title = default_title
    if not isinstance(title, str):
        raise ValueError("rubric.title must be a string")

    instructions = payload.get("instructions") or payload.get("prompt") or ""
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("rubric.instructions must be a non-empty string")

    criteria_raw = payload.get("criteria", [])
    if criteria_raw is None:
        criteria_raw = []
    if not isinstance(criteria_raw, list):
        raise ValueError("rubric.criteria must be an array")

    criteria: list[RubricCriterion] = []
    for item in criteria_raw:
        if not isinstance(item, dict):
            raise ValueError("each rubric criterion must be an object")
        cid = item.get("id") or item.get("name") or item.get("criterion_id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("criterion id/name must be a non-empty string")
        description = item.get("description") or item.get("reason") or cid
        if not isinstance(description, str) or not description.strip():
            raise ValueError("criterion description must be a non-empty string")
        weight = item.get("weight", 1.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("criterion.weight must be a number")
        criteria.append(
            RubricCriterion(
                id=cid.strip(),
                description=description.strip(),
                weight=float(weight),
            )
        )

    pass_threshold = _optional_float(payload, "pass_threshold", default=0.5)
    scale_min = _optional_float(payload, "scale_min", default=0.0)
    scale_max = _optional_float(payload, "scale_max", default=1.0)

    return RubricSpecification(
        title=title.strip(),
        instructions=instructions.strip(),
        criteria=tuple(criteria),
        pass_threshold=pass_threshold,
        scale_min=scale_min,
        scale_max=scale_max,
    )


def _optional_float(
    payload: dict[str, Any],
    key: str,
    *,
    default: float | None,
) -> float | None:
    if key not in payload or payload[key] is None:
        return default
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"rubric.{key} must be a number")
    return float(value)
