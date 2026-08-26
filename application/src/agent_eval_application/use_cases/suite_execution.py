"""Suite fan-out execution and deterministic result aggregation."""

from __future__ import annotations

from uuid import uuid4

from agent_eval_domain.common.ids import (
    AgentId,
    CaseVersionId,
    ProjectId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.versioning.status import VersionStatus

from agent_eval_application.adapter_capabilities import (
    AdapterSupportStatus,
    get_adapter_capability,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.commands.suite_execution import (
    AggregateSuiteResultsCommand,
    CreateSuiteRunsCommand,
)
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import RunDTO
from agent_eval_application.dto.suite_execution import (
    SuiteAggregateDTO,
    SuiteCaseResultDTO,
    SuiteExecutionDTO,
    SuiteRunEntryDTO,
)
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from agent_eval_application.run_identity import normalize_adapter_key
from agent_eval_application.scoring.aggregation import aggregate_scores
from agent_eval_application.use_cases.base import with_domain_errors
from agent_eval_application.use_cases.run import CreateRun


def _resolve_case_for_version(
    uow: UnitOfWork,
    *,
    project_id: ProjectId,
    case_version_id: CaseVersionId,
) -> tuple[object, object]:
    case_version = with_domain_errors(lambda: uow.cases.get_version(case_version_id))
    # CaseVersion carries case_id on the domain object.
    case = with_domain_errors(lambda: uow.cases.get(case_version.case_id))
    if case.project_id != project_id:
        raise ApplicationValidationError(
            "Suite case does not belong to the suite project",
            code="SUITE_CASE_PROJECT_MISMATCH",
            details={
                "case_id": case.id.value,
                "project_id": project_id.value,
                "case_version_id": case_version_id.value,
            },
        )
    if case_version.status not in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}:
        raise ApplicationValidationError(
            "Suite composition references a non-pinnable CaseVersion",
            code="SUITE_CASE_NOT_PINNABLE",
            details={
                "case_version_id": case_version_id.value,
                "status": case_version.status.value,
            },
        )
    if not case_version.reference_repository.commit_sha.strip():
        raise ApplicationValidationError(
            "CaseVersion is missing exact commit SHA",
            code="SUITE_CASE_MISSING_SHA",
            details={"case_version_id": case_version_id.value},
        )
    prompt_version = case.prompt.get_version(case_version.prompt_version_id)
    if not prompt_version.is_pinnable():
        raise ApplicationValidationError(
            "Suite case requires a published PromptVersion",
            code="SUITE_PROMPT_NOT_PINNABLE",
            details={
                "case_version_id": case_version_id.value,
                "prompt_version_id": prompt_version.id.value,
                "status": prompt_version.status.value,
            },
        )
    return case, case_version


def _resolve_grader_refs(
    uow: UnitOfWork,
    *,
    case_version: object,
    explicit: tuple[tuple[str, str], ...] | None,
) -> tuple[tuple[str, str], ...]:
    if explicit:
        return explicit
    refs: list[tuple[str, str]] = []
    applicable = getattr(case_version, "applicable_grader_ids", ())
    for grader_id in applicable:
        grader = with_domain_errors(lambda gid=grader_id: uow.graders.get(gid))
        active = grader.active_version()
        if active is None:
            raise ApplicationValidationError(
                f"Case declares grader {grader.name!r} with no active version",
                code="SUITE_GRADER_NO_ACTIVE_VERSION",
                details={"grader_id": grader.id.value},
            )
        refs.append((grader.id.value, active.id.value))
    if not refs:
        raise ApplicationValidationError(
            "CaseVersion has no applicable graders and no "
            "grader_version_refs were provided",
            code="SUITE_NO_GRADERS",
            details={
                "case_version_id": case_version.id.value,
            },
        )
    return tuple(refs)


def _assert_adapter_executable(uow: UnitOfWork, *, agent_id: str) -> str:
    """Reject adapters that are not production-executable (fail closed).

    Returns the normalized adapter key for logging/details.
    """
    agent = with_domain_errors(
        lambda: uow.agents.get(AgentId(require_non_empty(agent_id, field="agent_id")))
    )
    if agent.adapter_id is None:
        raise ApplicationValidationError(
            "Agent has no connected Adapter",
            code="AGENT_MISSING_ADAPTER",
            details={"agent_id": agent.id.value},
        )
    adapter = with_domain_errors(lambda: uow.adapters.get(agent.adapter_id))
    key = normalize_adapter_key(adapter.name)
    if key is None:
        raise ApplicationValidationError(
            f"Adapter {adapter.name!r} is not a recognized coding-agent adapter",
            code="ADAPTER_UNKNOWN",
            details={"adapter_id": adapter.id.value, "adapter_name": adapter.name},
        )
    capability = get_adapter_capability(key)
    if capability is None or capability.status in {
        AdapterSupportStatus.UNSUPPORTED,
        AdapterSupportStatus.IMPLEMENTED_UNVERIFIED,
    }:
        raise ApplicationValidationError(
            f"Adapter {key!r} is not executable on EvalForge "
            f"(status={getattr(capability, 'status', None)})",
            code="ADAPTER_UNSUPPORTED",
            details={
                "adapter_key": key,
                "adapter_id": adapter.id.value,
                "status": (
                    capability.status.value if capability is not None else "unknown"
                ),
            },
        )
    return key


class CreateSuiteRuns:
    """Validate suite composition, then create+enqueue one Run per case."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        create_run: CreateRun,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._create_run = create_run

    def execute(self, command: CreateSuiteRunsCommand) -> SuiteExecutionDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))
        version_id = SuiteVersionId(
            require_non_empty(command.suite_version_id, field="suite_version_id")
        )
        execution_group_id = (
            command.execution_group_id.strip()
            if command.execution_group_id and command.execution_group_id.strip()
            else str(uuid4())
        )

        with self._uow_factory() as uow:
            suite = with_domain_errors(lambda: uow.suites.get(suite_id))
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            suite_version = suite.get_version(version_id)
            if suite_version.status not in {
                VersionStatus.ACTIVE,
                VersionStatus.SUPERSEDED,
            }:
                raise ApplicationValidationError(
                    "SuiteVersion must be published (ACTIVE or SUPERSEDED) to execute",
                    code="SUITE_VERSION_NOT_EXECUTABLE",
                    details={
                        "suite_version_id": version_id.value,
                        "status": suite_version.status.value,
                    },
                )
            if not suite_version.composition:
                raise ApplicationValidationError(
                    "SuiteVersion composition is empty",
                    code="SUITE_COMPOSITION_EMPTY",
                    details={"suite_version_id": version_id.value},
                )

            _assert_adapter_executable(uow, agent_id=command.agent_id)

            # Validate every case before creating any runs.
            planned: list[tuple[int, object, object, tuple[tuple[str, str], ...]]] = []
            for entry in sorted(suite_version.composition, key=lambda e: e.position):
                case, case_version = _resolve_case_for_version(
                    uow,
                    project_id=suite.project_id,
                    case_version_id=entry.case_version_id,
                )
                grader_refs = _resolve_grader_refs(
                    uow,
                    case_version=case_version,
                    explicit=command.grader_version_refs,
                )
                planned.append((entry.position, case, case_version, grader_refs))

            project_id = suite.project_id.value

        # Create runs outside the validation UoW so each CreateRun owns its txn.
        entries: list[SuiteRunEntryDTO] = []
        for position, case, case_version, grader_refs in planned:
            run = self._create_run.execute(
                CreateRunCommand(
                    actor=command.actor,
                    project_id=project_id,
                    case_id=case.id.value,
                    case_version_id=case_version.id.value,
                    prompt_version_id=case_version.prompt_version_id.value,
                    agent_id=command.agent_id,
                    agent_version_id=command.agent_version_id,
                    adapter_version_id=command.adapter_version_id,
                    grader_version_refs=grader_refs,
                    platform_version_id=command.platform_version_id,
                    suite_id=suite_id.value,
                    suite_version_id=version_id.value,
                    execution_group_id=execution_group_id,
                    idempotency_key=(
                        f"{command.idempotency_key}:{case_version.id.value}"
                        if command.idempotency_key
                        else None
                    ),
                )
            )
            entries.append(
                SuiteRunEntryDTO(
                    case_version_id=case_version.id.value,
                    position=position,
                    run=run,
                    aggregate=aggregate_scores(run.scores),
                )
            )

        return SuiteExecutionDTO(
            suite_id=suite_id.value,
            suite_version_id=version_id.value,
            execution_group_id=execution_group_id,
            total_cases=len(entries),
            runs=tuple(entries),
        )


class AggregateSuiteResults:
    """Deterministic suite rollup over Runs pinned to a SuiteVersion."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, command: AggregateSuiteResultsCommand) -> SuiteAggregateDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))
        version_id = SuiteVersionId(
            require_non_empty(command.suite_version_id, field="suite_version_id")
        )
        group_id = (
            command.execution_group_id.strip()
            if command.execution_group_id and command.execution_group_id.strip()
            else None
        )
        with self._uow_factory() as uow:
            suite = with_domain_errors(lambda: uow.suites.get(suite_id))
            self._auth.ensure_can_access_project(command.actor, suite.project_id)
            suite_version = suite.get_version(version_id)
            runs = []
            for run in uow.runs.list_by_project(suite.project_id):
                if (
                    run.pins.suite_version_id is None
                    or run.pins.suite_version_id.value != version_id.value
                ):
                    continue
                if group_id is not None and run.execution_group_id != group_id:
                    continue
                runs.append(run)

            composition_ids = {
                entry.case_version_id.value for entry in suite_version.composition
            }
            case_results: list[SuiteCaseResultDTO] = []
            completed = failed = cancelled = queued = passed = 0
            evaluation_failed = objective_failed_count = 0
            score_values: list[float] = []

            for run in runs:
                dto = RunDTO.from_domain(run)
                agg = aggregate_scores(dto.scores)
                status = dto.status
                if status == "completed":
                    completed += 1
                    if agg.passed is False:
                        evaluation_failed += 1
                elif status == "failed":
                    failed += 1
                elif status == "cancelled":
                    cancelled += 1
                else:
                    queued += 1
                if agg.passed is True:
                    passed += 1
                if agg.objective_failed:
                    objective_failed_count += 1
                if agg.overall_score is not None:
                    score_values.append(agg.overall_score)

                case_name: str | None = None
                case_id: str | None = None
                category: str | None = None
                difficulty: str | None = None
                try:
                    case_version = uow.cases.get_version(
                        CaseVersionId(dto.pins.case_version_id)
                    )
                    case = uow.cases.get(case_version.case_id)
                    case_id = case.id.value
                    case_name = case.name
                    category = case.category or None
                    difficulty = case.difficulty or None
                except Exception:  # noqa: BLE001 — best-effort labels
                    pass

                case_results.append(
                    SuiteCaseResultDTO(
                        case_version_id=dto.pins.case_version_id,
                        run_id=dto.id,
                        status=status,
                        aggregate=agg,
                        failure_reason=dto.failure_reason,
                        failure_category=dto.failure_category,
                        case_id=case_id,
                        case_name=case_name,
                        category=category,
                        difficulty=difficulty,
                    )
                )

            # Stable order: composition position, then run id.
            position = {
                e.case_version_id.value: e.position for e in suite_version.composition
            }
            case_results.sort(
                key=lambda row: (
                    position.get(row.case_version_id, 10_000),
                    row.run_id,
                )
            )

            decided = sum(1 for r in case_results if r.aggregate.passed is not None)
            pass_rate = (passed / decided) if decided else None
            average_score = (
                sum(score_values) / len(score_values) if score_values else None
            )

            return SuiteAggregateDTO(
                suite_id=suite_id.value,
                suite_version_id=version_id.value,
                execution_group_id=group_id,
                total_cases=len(composition_ids),
                run_count=len(case_results),
                completed=completed,
                failed=failed,
                execution_failed=failed,
                cancelled=cancelled,
                queued_or_running=queued,
                passed=passed,
                evaluation_failed=evaluation_failed,
                objective_failed_count=objective_failed_count,
                pass_rate=pass_rate,
                average_score=average_score,
                cases=tuple(case_results),
            )
