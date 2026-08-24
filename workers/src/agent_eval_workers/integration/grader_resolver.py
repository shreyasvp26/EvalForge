"""Resolve pinned Grader Versions into concrete Grader SDK invocations.

Phase 1 canonical path: objective ``ExpectedFileGrader`` / ``DiffValidationGrader``
from published grader pins. Rubric graders require an injectable judge and are
skipped unless a factory is supplied.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListGradersQuery
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import DiffValidationGrader, ExpectedFileGrader
from agent_eval_graders.sdk.grader import Grader

from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec

GraderFactory = Callable[[], Grader]


def _parse_expected_paths(specification: str) -> tuple[str, ...]:
    raw = specification.strip()
    if not raw:
        return ("main.py",)
    # JSON-ish list: ["a.py", "b.py"]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return ("main.py",)
        parts = [p.strip().strip("\"'") for p in inner.split(",")]
        paths = tuple(p for p in parts if p)
        return paths or ("main.py",)
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        paths = tuple(p for p in parts if p)
        return paths or ("main.py",)
    # Single path or free-form label — prefer path-like tokens.
    if "/" in raw or "." in raw.split()[0]:
        return (raw.split()[0],)
    return ("main.py",)


def _objective_factory(*, name: str, specification: str) -> GraderFactory:
    lowered = f"{name} {specification}".lower()
    if "diff" in lowered:
        return DiffValidationGrader
    paths = _parse_expected_paths(specification)
    return lambda: ExpectedFileGrader(expected_paths=paths)


@dataclass(slots=True)
class PinBasedGraderResolver:
    """Build ``GraderInvocationSpec`` rows from Run pins + Grader catalog."""

    actor: Actor
    get_run: object
    list_graders: object
    rubric_factory: Callable[[str, str, str], GraderFactory] | None = None

    def resolve(self, run_id: RunId) -> tuple[GraderInvocationSpec, ...]:
        run = self.get_run.execute(  # type: ignore[attr-defined]
            GetRunQuery(actor=self.actor, run_id=run_id.value)
        )
        graders = self.list_graders.execute(  # type: ignore[attr-defined]
            ListGradersQuery(actor=self.actor)
        )
        by_version: dict[str, tuple[object, object]] = {}
        for grader in graders:
            for version in grader.versions:
                by_version[version.id] = (grader, version)

        specs: list[GraderInvocationSpec] = []
        for version_id in run.pins.grader_version_ids:
            matched = by_version.get(version_id)
            if matched is None:
                raise LookupError(
                    f"Pinned grader version {version_id!r} not found in catalog"
                )
            grader, version = matched
            family = str(grader.family).lower()
            name = str(grader.name)
            specification = str(version.specification)
            label = str(version.label)

            if family == "rubric":
                if self.rubric_factory is None:
                    # Phase 1: skip rubric pins when no judge is configured.
                    continue
                factory = self.rubric_factory(name, specification, label)
            else:
                factory = _objective_factory(name=name, specification=specification)

            specs.append(
                GraderInvocationSpec(
                    name=name or f"grader-{version_id[:8]}",
                    grader_id=str(grader.id),
                    grader_version_id=version_id,
                    factory=factory,
                    specification=specification,
                    version_label=label,
                )
            )

        if not specs:
            raise LookupError(
                "No invocable graders resolved from Run pins "
                "(objective graders required for Phase 1; rubric needs a judge)"
            )
        return tuple(specs)
