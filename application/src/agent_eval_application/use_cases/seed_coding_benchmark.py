"""Seed the EvalForge Coding Benchmark v1 suite into a project."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.benchmark_catalog import (
    CODING_BENCHMARK_V1_REPO,
    CODING_BENCHMARK_V1_SHA,
    CODING_BENCHMARK_V1_TASKS,
    WORKSPACE_PYTEST_SPEC,
)
from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    PublishCaseVersionCommand,
)
from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.platform import (
    CreatePlatformCommand,
    CreatePlatformDraftVersionCommand,
    PublishPlatformVersionCommand,
)
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.commands.suite import (
    CreateSuiteCommand,
    CreateSuiteDraftVersionCommand,
    PublishSuiteVersionCommand,
    SuiteCompositionEntryInput,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.suite import SuiteDTO
from agent_eval_application.queries.queries import GetSuiteQuery
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.platform import (
    CreatePlatform,
    CreatePlatformDraftVersion,
    PublishPlatformVersion,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    GetSuite,
    PublishSuiteVersion,
)


@dataclass(frozen=True, slots=True)
class SeededCodingBenchmark:
    project_id: str
    suite_id: str
    suite_version_id: str
    platform_version_id: str
    grader_id: str
    grader_version_id: str
    case_version_ids: tuple[str, ...]
    suite: SuiteDTO


@dataclass(slots=True)
class SeedCodingBenchmarkV1:
    """Create a published catalog-visible suite composed of five pinned cases."""

    create_project: CreateProject
    create_grader: CreateGrader
    create_grader_draft: CreateGraderDraftVersion
    publish_grader: PublishGraderVersion
    create_platform: CreatePlatform
    create_platform_draft: CreatePlatformDraftVersion
    publish_platform: PublishPlatformVersion
    create_case: CreateCase
    create_prompt_draft: CreatePromptDraftVersion
    create_case_draft: CreateCaseDraftVersion
    publish_case: PublishCaseVersion
    create_suite: CreateSuite
    create_suite_draft: CreateSuiteDraftVersion
    publish_suite: PublishSuiteVersion
    get_suite: GetSuite

    def execute(
        self,
        *,
        actor: Actor,
        project_name: str = "EvalForge Coding Benchmark",
        suite_name: str = "EvalForge Coding Benchmark v1",
    ) -> SeededCodingBenchmark:
        project = self.create_project.execute(
            CreateProjectCommand(
                actor=actor,
                name=project_name,
                description="Canonical Phase 10 reproducible coding benchmark",
            )
        )
        grader = self.create_grader.execute(
            CreateGraderCommand(
                actor=actor,
                name="workspace-pytest",
                family="objective",
            )
        )
        grader_draft = self.create_grader_draft.execute(
            CreateGraderDraftVersionCommand(
                actor=actor,
                grader_id=grader.id,
                label="workspace-pytest-v1",
                specification=WORKSPACE_PYTEST_SPEC,
            )
        )
        grader_version = self.publish_grader.execute(
            PublishGraderVersionCommand(
                actor=actor,
                grader_id=grader.id,
                version_id=grader_draft.id,
            )
        )
        platform = self.create_platform.execute(
            CreatePlatformCommand(actor=actor, name="evalforge-default")
        )
        platform_draft = self.create_platform_draft.execute(
            CreatePlatformDraftVersionCommand(
                actor=actor,
                platform_id=platform.id,
                label="1.0",
                sandbox_policy={"engine": "docker"},
                notes="Default sandbox platform for coding benchmarks",
            )
        )
        platform_version = self.publish_platform.execute(
            PublishPlatformVersionCommand(
                actor=actor,
                platform_id=platform.id,
                version_id=platform_draft.id,
            )
        )

        composition: list[SuiteCompositionEntryInput] = []
        case_version_ids: list[str] = []
        for position, task in enumerate(CODING_BENCHMARK_V1_TASKS):
            case = self.create_case.execute(
                CreateCaseCommand(
                    actor=actor,
                    project_id=project.id,
                    name=task.title,
                    description=task.description,
                    category=task.category,
                    difficulty=task.difficulty,
                    language="python",
                    tags=task.tags,
                )
            )
            prompt = self.create_prompt_draft.execute(
                CreatePromptDraftVersionCommand(
                    actor=actor,
                    case_id=case.id,
                    content=task.prompt,
                )
            )
            case_draft = self.create_case_draft.execute(
                CreateCaseDraftVersionCommand(
                    actor=actor,
                    case_id=case.id,
                    description=task.description,
                    repository_url=CODING_BENCHMARK_V1_REPO,
                    commit_sha=CODING_BENCHMARK_V1_SHA,
                    subdirectory=task.subdirectory,
                    expected_checks=("pytest",),
                    applicable_grader_ids=(grader.id,),
                    prompt_version_id=prompt.id,
                )
            )
            case_version = self.publish_case.execute(
                PublishCaseVersionCommand(
                    actor=actor,
                    case_id=case.id,
                    version_id=case_draft.id,
                )
            )
            case_version_ids.append(case_version.id)
            composition.append(
                SuiteCompositionEntryInput(
                    case_version_id=case_version.id,
                    position=position,
                    case_project_id=project.id,
                )
            )

        suite = self.create_suite.execute(
            CreateSuiteCommand(
                actor=actor,
                project_id=project.id,
                name=suite_name,
                description=(
                    "Five deterministic Python coding tasks with pinned SHAs "
                    "and workspace pytest graders."
                ),
                catalog_key="coding-benchmark-v1",
                catalog_visible=True,
            )
        )
        suite_draft = self.create_suite_draft.execute(
            CreateSuiteDraftVersionCommand(
                actor=actor,
                suite_id=suite.id,
                composition=tuple(composition),
            )
        )
        suite_version = self.publish_suite.execute(
            PublishSuiteVersionCommand(
                actor=actor,
                suite_id=suite.id,
                version_id=suite_draft.id,
            )
        )
        suite = self.get_suite.execute(GetSuiteQuery(actor=actor, suite_id=suite.id))
        return SeededCodingBenchmark(
            project_id=project.id,
            suite_id=suite.id,
            suite_version_id=suite_version.id,
            platform_version_id=platform_version.id,
            grader_id=grader.id,
            grader_version_id=grader_version.id,
            case_version_ids=tuple(case_version_ids),
            suite=suite,
        )
