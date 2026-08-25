"""GradingSchedulerPort ← Grader SDK (objective + rubric) + Application scores."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import GraderId, GraderVersionId, RunId
from agent_eval_graders.sdk import (
    GradingConfig,
    GradingContext,
    run_graders_isolated,
)
from agent_eval_graders.sdk.grader import Grader
from agent_eval_graders.sdk.models import ProducedScore

from agent_eval_workers.integration.run_reader import ApplicationRunReader
from agent_eval_workers.integration.score_sink import ApplicationScoreSink

GraderFactory = Callable[[], Grader]
GraderSpecResolver = Callable[[RunId], Sequence["GraderInvocationSpec"]]
WorkspaceProbe = Callable[[RunId, Sequence["GraderInvocationSpec"]], None]


@dataclass(frozen=True, slots=True)
class GraderInvocationSpec:
    """One pinned Grader Version to invoke after execution completes."""

    name: str
    grader_id: str
    grader_version_id: str
    factory: GraderFactory
    specification: str = ""
    version_label: str = "v1"


@dataclass
class GraderSdkScheduler:
    """``GradingSchedulerPort`` — isolated Grader SDK invocations + RecordScore.

    Never runs during Adapter execution. Sibling failures stay local via
    ``run_graders_isolated``.
    """

    actor: Actor
    get_run: object
    get_events: object
    get_artifacts: object
    record_score: object
    graders: Sequence[GraderInvocationSpec] = ()
    grader_resolver: GraderSpecResolver | None = None
    workspace_probe: WorkspaceProbe | None = None
    scores: list[ProducedScore] = field(default_factory=list)
    failures: list[tuple[str, str, str]] = field(default_factory=list)
    scheduled: list[RunId] = field(default_factory=list)
    after_schedule: Callable[[RunId], None] | None = None

    def schedule(self, run_id: RunId) -> None:
        self.scheduled.append(run_id)
        reader = ApplicationRunReader(
            run_id=run_id,
            actor=self.actor,
            get_run=self.get_run,
            get_events=self.get_events,
            get_artifacts=self.get_artifacts,
        )
        sink = ApplicationScoreSink(
            record_score=self.record_score,
            actor=self.actor,
        )
        specs = (
            tuple(self.grader_resolver(run_id))
            if self.grader_resolver is not None
            else tuple(self.graders)
        )
        if self.workspace_probe is not None:
            self.workspace_probe(run_id, specs)
        workspace_results = None
        if self.workspace_probe is not None and hasattr(
            self.workspace_probe, "workspace_results"
        ):
            workspace_results = self.workspace_probe.workspace_results()  # type: ignore[attr-defined]
        invocations: list[tuple[str, Grader, GradingContext]] = []
        for spec in specs:
            context = GradingContext(
                reader=reader,
                grader_id=GraderId(spec.grader_id),
                grader_version_id=GraderVersionId(spec.grader_version_id),
                grader_version_label=spec.version_label,
                grader_specification=spec.specification,
                correlation_id=f"grade-{run_id.value}-{spec.name}",
                config=GradingConfig(timeout_seconds=60.0),
                workspace_test_results=workspace_results,
            )
            invocations.append((spec.name, spec.factory(), context))

        result = run_graders_isolated(invocations, sink=sink)
        self.scores.extend(result.scores)
        self.failures.extend(result.failures)
        if self.after_schedule is not None:
            self.after_schedule(run_id)
