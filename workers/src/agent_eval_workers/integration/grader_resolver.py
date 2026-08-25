"""Resolve pinned Grader Versions into concrete Grader SDK invocations.

Maps objective pins to the built-in objective grader family. Rubric graders
require an injectable judge factory. When a rubric is pinned and no judge is
configured, resolution fails closed — never silently skip a required pin.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListGradersQuery
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import (
    BuildSuccessGrader,
    DiffValidationGrader,
    ExitCodeGrader,
    ExpectedFileGrader,
    JSONOutputGrader,
    LintGrader,
    TestPassGrader,
)
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


def _parse_required_keys(specification: str) -> tuple[str, ...]:
    raw = specification.strip()
    if not raw:
        return ()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return ()
        return tuple(p.strip().strip("\"'") for p in inner.split(",") if p.strip())
    if "," in raw:
        return tuple(p.strip() for p in raw.split(",") if p.strip())
    # Treat free-form non-path labels as a single required key when plausible.
    token = raw.split()[0]
    if "/" not in token and "." not in token:
        return (token,)
    return ()


def _objective_factory(*, name: str, specification: str) -> GraderFactory:
    """Map grader identity + specification heuristics to an objective factory."""
    lowered = f"{name} {specification}".lower()

    if "diff" in lowered:
        return DiffValidationGrader
    if "build" in lowered:
        return BuildSuccessGrader
    if "test" in lowered and "expected" not in lowered:
        return TestPassGrader
    if "lint" in lowered:
        return LintGrader
    if "exit" in lowered or "exit_code" in lowered.replace(" ", "_"):
        return ExitCodeGrader
    if "json" in lowered:
        keys = _parse_required_keys(specification)
        return lambda: JSONOutputGrader(required_keys=keys)
    if "expected" in lowered or "file" in lowered:
        paths = _parse_expected_paths(specification)
        return lambda: ExpectedFileGrader(expected_paths=paths)

    # Default: path-oriented ExpectedFile — preserves Phase 1 behavior for
    # free-form objective grader names that declare file paths in the spec.
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
                    raise LookupError(
                        f"Pinned rubric grader {name!r} (version {version_id}) "
                        "requires a configured LLM judge; no judge is available. "
                        "Configure a judge provider or pin only objective graders."
                    )
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
                "(at least one published grader version must be pinned)"
            )
        return tuple(specs)
