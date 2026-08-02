"""SQLAlchemy RunRepository adapter."""

from __future__ import annotations

from agent_eval_domain.common.ids import ProjectId, RunId
from agent_eval_domain.execution.run import EvaluationRun
from sqlalchemy import select

from agent_eval_infrastructure.database.models.execution.artifact import ArtifactOrm
from agent_eval_infrastructure.database.models.execution.event import ExecutionEventOrm
from agent_eval_infrastructure.database.models.execution.run import RunOrm
from agent_eval_infrastructure.database.models.execution.score import ScoreOrm
from agent_eval_infrastructure.mappers.common import require_found
from agent_eval_infrastructure.mappers.run import (
    apply_run_to_orm,
    artifact_to_orm,
    execution_event_to_orm,
    new_run_orm,
    run_to_domain,
    score_to_orm,
)
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository


class SqlAlchemyRunRepository(SqlAlchemyRepository):
    def get(self, run_id: RunId) -> EvaluationRun:
        row = self.session.get(RunOrm, run_id.value)
        require_found(row, entity_type="Run", entity_id=run_id.value)
        return self._load_run(row)  # type: ignore[arg-type]

    def save(self, run: EvaluationRun) -> None:
        row = self.session.get(RunOrm, run.id.value)
        if row is None:
            row = new_run_orm(run)
            self.session.add(row)
        else:
            apply_run_to_orm(run, row)

        existing_event_ids = set(
            self.session.scalars(
                select(ExecutionEventOrm.id).where(
                    ExecutionEventOrm.run_id == run.id.value
                )
            )
        )
        for event in run.execution_events:
            if event.id.value not in existing_event_ids:
                self.session.add(execution_event_to_orm(event))

        existing_artifact_ids = set(
            self.session.scalars(
                select(ArtifactOrm.id).where(ArtifactOrm.run_id == run.id.value)
            )
        )
        for artifact in run.artifacts:
            if artifact.id.value not in existing_artifact_ids:
                self.session.add(artifact_to_orm(artifact))

        existing_score_ids = set(
            self.session.scalars(
                select(ScoreOrm.id).where(ScoreOrm.run_id == run.id.value)
            )
        )
        for score in run.scores:
            if score.id.value not in existing_score_ids:
                self.session.add(score_to_orm(score))

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationRun]:
        rows = list(
            self.session.scalars(
                select(RunOrm)
                .where(RunOrm.project_id == project_id.value)
                .order_by(RunOrm.created_at.desc())
            )
        )
        return [self._load_run(row) for row in rows]

    def _load_run(self, row: RunOrm) -> EvaluationRun:
        events = list(
            self.session.scalars(
                select(ExecutionEventOrm).where(ExecutionEventOrm.run_id == row.id)
            )
        )
        artifacts = list(
            self.session.scalars(
                select(ArtifactOrm).where(ArtifactOrm.run_id == row.id)
            )
        )
        scores = list(
            self.session.scalars(select(ScoreOrm).where(ScoreOrm.run_id == row.id))
        )
        return run_to_domain(row, events, artifacts, scores)
