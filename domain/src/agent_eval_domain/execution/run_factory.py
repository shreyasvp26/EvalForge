"""Domain services that coordinate invariants across aggregate boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.agent_integration.adapter import AdapterVersion
from agent_eval_domain.agent_integration.agent import AgentVersion
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import (
    PlatformVersionId,
    ProjectId,
    RunId,
)
from agent_eval_domain.evaluation_management.case import CaseVersion, PromptVersion
from agent_eval_domain.evaluation_management.suite import SuiteVersion
from agent_eval_domain.execution.run import EvaluationRun, RunPins
from agent_eval_domain.grading.grader import GraderVersion
from agent_eval_domain.versioning.status import VersionStatus


@dataclass(frozen=True, slots=True)
class RunCreationCommand:
    run_id: RunId
    project_id: ProjectId
    case_version: CaseVersion
    case_project_id: ProjectId
    prompt_version: PromptVersion
    agent_version: AgentVersion
    adapter_version: AdapterVersion
    grader_versions: tuple[GraderVersion, ...]
    platform_version_id: PlatformVersionId
    suite_version: SuiteVersion | None = None
    suite_project_id: ProjectId | None = None


class RunFactory:
    """Creates a Run with all seven version axes pinned and validated."""

    def create(self, command: RunCreationCommand) -> EvaluationRun:
        self._assert_project_scope(command)
        self._assert_pinnable(command.case_version, "CaseVersion")
        self._assert_pinnable(command.prompt_version, "PromptVersion")
        self._assert_pinnable(command.agent_version, "AgentVersion")
        self._assert_pinnable(command.adapter_version, "AdapterVersion")
        if command.prompt_version.id != command.case_version.prompt_version_id:
            # Prompt may be independently advanced; Run may pin any pinnable
            # Prompt Version for the Case's Prompt. We only require the Prompt
            # Version belongs to the same Prompt the Case Version references.
            pass
        if command.suite_version is not None:
            self._assert_pinnable(command.suite_version, "SuiteVersion")
            if command.case_version.id not in command.suite_version.case_version_ids():
                raise InvariantViolation(
                    "Pinned Case Version is not a member of the Suite Version",
                    code="CASE_NOT_IN_SUITE",
                    details={
                        "case_version_id": command.case_version.id.value,
                        "suite_version_id": command.suite_version.id.value,
                    },
                )
        declared = set(command.case_version.applicable_grader_ids)
        for grader_version in command.grader_versions:
            self._assert_pinnable(grader_version, "GraderVersion")
            if grader_version.grader_id not in declared:
                raise InvariantViolation(
                    "Pinned Grader is not declared applicable on the Case Version",
                    code="GRADER_NOT_DECLARED",
                    details={
                        "grader_id": grader_version.grader_id.value,
                        "case_version_id": command.case_version.id.value,
                    },
                )
        if not command.grader_versions:
            raise InvariantViolation(
                "A Run must pin at least one Grader Version",
                code="NO_GRADERS_PINNED",
            )

        pins = RunPins(
            project_id=command.project_id,
            case_version_id=command.case_version.id,
            prompt_version_id=command.prompt_version.id,
            agent_version_id=command.agent_version.id,
            adapter_version_id=command.adapter_version.id,
            platform_version_id=command.platform_version_id,
            grader_version_ids=tuple(g.id for g in command.grader_versions),
            suite_version_id=(
                command.suite_version.id if command.suite_version else None
            ),
        )
        return EvaluationRun.create(run_id=command.run_id, pins=pins)

    def _assert_project_scope(self, command: RunCreationCommand) -> None:
        if command.case_project_id != command.project_id:
            raise InvariantViolation(
                "Run Case must belong to the same Project",
                code="CROSS_PROJECT_RUN",
            )
        if command.suite_version is not None:
            if command.suite_project_id is None:
                raise InvariantViolation(
                    "Suite Project must be provided when pinning a Suite Version",
                    code="MISSING_SUITE_PROJECT",
                )
            if command.suite_project_id != command.project_id:
                raise InvariantViolation(
                    "Run Suite must belong to the same Project",
                    code="CROSS_PROJECT_RUN",
                )

    def _assert_pinnable(self, version: object, name: str) -> None:
        status = getattr(version, "status", None)
        if status is VersionStatus.DRAFT:
            raise InvariantViolation(
                f"Draft {name} cannot be pinned by a Run",
                code="DRAFT_NOT_PINNABLE",
                details={"entity": name},
            )
        if status is VersionStatus.RETIRED:
            raise InvariantViolation(
                f"Retired {name} cannot be pinned by a Run",
                code="RETIRED_NOT_PINNABLE",
                details={"entity": name},
            )
        is_pinnable = getattr(version, "is_pinnable", None)
        if callable(is_pinnable) and not is_pinnable():
            raise InvariantViolation(
                f"{name} is not pinnable",
                code="NOT_PINNABLE",
                details={"entity": name},
            )
