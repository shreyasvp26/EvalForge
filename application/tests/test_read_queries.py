"""Application read-query use case tests (no FastAPI / SQLAlchemy)."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAdapterVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    PublishCaseVersionCommand,
    PublishPromptVersionCommand,
)
from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.commands.run import (
    CreateRunCommand,
    RecordArtifactCommand,
    RecordExecutionEventCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import (
    AuthorizationError,
    NotFoundApplicationError,
)
from agent_eval_application.queries.queries import (
    GetAdapterQuery,
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunScoresQuery,
    ListAdaptersQuery,
    ListAgentsQuery,
    ListGradersQuery,
    ListProjectsQuery,
)
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    GetAdapter,
    ListAdapters,
    ListAgents,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
    PublishPromptVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    ListGraders,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.project import CreateProject, ListProjects
from agent_eval_application.use_cases.run import (
    CreateRun,
    GetRunArtifacts,
    GetRunEvents,
    GetRunScores,
    RecordArtifact,
    RecordExecutionEvent,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_domain.common.ids import ProjectId
from fakes import (
    AllowAllAuth,
    DenyAllAuth,
    InMemoryIdempotencyStore,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    RecordingRunQueue,
    SharedStore,
)


class SelectiveProjectAuth(AllowAllAuth):
    """Allow access only to explicitly permitted project ids."""

    def __init__(self, allowed: set[str]) -> None:
        self._allowed = allowed

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        if project_id.value not in self._allowed:
            raise AuthorizationError(details={"project_id": project_id.value})


@pytest.fixture
def harness():
    store = SharedStore()
    return {
        "store": store,
        "uow": InMemoryUnitOfWorkFactory(store),
        "ids": InMemoryIdGenerator("id"),
        "auth": AllowAllAuth(),
        "events": RecordingEventDispatcher(),
        "queue": RecordingRunQueue(),
        "idempotency": InMemoryIdempotencyStore(),
        "actor": Actor(id="user-1"),
    }


@pytest.fixture
def run_world(harness):
    """Published Project / Case / Agent / Adapter / Grader graph for Run reads."""
    uow = harness["uow"]
    ids = harness["ids"]
    auth = harness["auth"]
    events = harness["events"]
    actor = harness["actor"]

    project = CreateProject(uow, ids, auth, events).execute(
        CreateProjectCommand(actor=actor, name="P")
    )
    grader = CreateGrader(uow, ids, auth, events).execute(
        CreateGraderCommand(actor=actor, name="G", family="objective")
    )
    gv = CreateGraderDraftVersion(uow, ids, auth, events).execute(
        CreateGraderDraftVersionCommand(
            actor=actor,
            grader_id=grader.id,
            label="v1",
            specification="ok",
        )
    )
    gv = PublishGraderVersion(uow, auth, events).execute(
        PublishGraderVersionCommand(actor=actor, grader_id=grader.id, version_id=gv.id)
    )

    case = CreateCase(uow, ids, auth, events).execute(
        CreateCaseCommand(actor=actor, project_id=project.id, name="C")
    )
    pv = CreatePromptDraftVersion(uow, ids, auth, events).execute(
        CreatePromptDraftVersionCommand(actor=actor, case_id=case.id, content="Fix it")
    )
    PublishPromptVersion(uow, auth, events).execute(
        PublishPromptVersionCommand(actor=actor, case_id=case.id, version_id=pv.id)
    )
    cv = CreateCaseDraftVersion(uow, ids, auth, events).execute(
        CreateCaseDraftVersionCommand(
            actor=actor,
            case_id=case.id,
            description="Fix the bug",
            repository_url="https://example.com/r.git",
            commit_sha="deadbeef",
            expected_checks=("pytest",),
            applicable_grader_ids=(grader.id,),
            prompt_version_id=pv.id,
        )
    )
    cv = PublishCaseVersion(uow, auth, events).execute(
        PublishCaseVersionCommand(actor=actor, case_id=case.id, version_id=cv.id)
    )

    agent = CreateAgent(uow, ids, auth, events).execute(
        CreateAgentCommand(actor=actor, name="Agent")
    )
    adapter = CreateAdapter(uow, ids, auth, events).execute(
        CreateAdapterCommand(actor=actor, agent_id=agent.id, name="Adapter")
    )
    av = CreateAgentDraftVersion(uow, ids, auth, events).execute(
        CreateAgentDraftVersionCommand(actor=actor, agent_id=agent.id, label="1.0")
    )
    av = PublishAgentVersion(uow, auth, events).execute(
        PublishAgentVersionCommand(actor=actor, agent_id=agent.id, version_id=av.id)
    )
    adv = CreateAdapterDraftVersion(uow, ids, auth, events).execute(
        CreateAdapterDraftVersionCommand(
            actor=actor, adapter_id=adapter.id, label="1.0"
        )
    )
    adv = PublishAdapterVersion(uow, auth, events).execute(
        PublishAdapterVersionCommand(
            actor=actor, adapter_id=adapter.id, version_id=adv.id
        )
    )

    return {
        **harness,
        "project_id": project.id,
        "case_id": case.id,
        "case_version_id": cv.id,
        "prompt_version_id": pv.id,
        "agent_id": agent.id,
        "agent_version_id": av.id,
        "adapter_version_id": adv.id,
        "grader_id": grader.id,
        "grader_version_id": gv.id,
    }


def test_list_projects_returns_visible_only(harness):
    create = CreateProject(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    )
    a = create.execute(CreateProjectCommand(actor=harness["actor"], name="A"))
    create.execute(CreateProjectCommand(actor=harness["actor"], name="B"))

    listed = ListProjects(harness["uow"], harness["auth"]).execute(
        ListProjectsQuery(actor=harness["actor"])
    )
    assert len(listed) == 2

    filtered = ListProjects(harness["uow"], SelectiveProjectAuth({a.id})).execute(
        ListProjectsQuery(actor=harness["actor"])
    )
    assert [p.id for p in filtered] == [a.id]


def test_list_agents_adapters_graders(harness):
    agent = CreateAgent(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(CreateAgentCommand(actor=harness["actor"], name="Claude"))
    adapter = CreateAdapter(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateAdapterCommand(
            actor=harness["actor"], agent_id=agent.id, name="claude-adapter"
        )
    )
    grader = CreateGrader(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateGraderCommand(actor=harness["actor"], name="tests", family="objective")
    )

    agents = ListAgents(harness["uow"], harness["auth"]).execute(
        ListAgentsQuery(actor=harness["actor"])
    )
    adapters = ListAdapters(harness["uow"], harness["auth"]).execute(
        ListAdaptersQuery(actor=harness["actor"])
    )
    graders = ListGraders(harness["uow"], harness["auth"]).execute(
        ListGradersQuery(actor=harness["actor"])
    )

    assert [item.id for item in agents] == [agent.id]
    assert [item.id for item in adapters] == [adapter.id]
    assert [item.id for item in graders] == [grader.id]

    got = GetAdapter(harness["uow"], harness["auth"]).execute(
        GetAdapterQuery(actor=harness["actor"], adapter_id=adapter.id)
    )
    assert got.id == adapter.id
    assert got.agent_id == agent.id


def test_get_adapter_not_found(harness):
    with pytest.raises(NotFoundApplicationError):
        GetAdapter(harness["uow"], harness["auth"]).execute(
            GetAdapterQuery(actor=harness["actor"], adapter_id="missing")
        )


def test_list_catalog_requires_auth(harness):
    with pytest.raises(AuthorizationError):
        ListAgents(harness["uow"], DenyAllAuth()).execute(
            ListAgentsQuery(actor=harness["actor"])
        )
    with pytest.raises(AuthorizationError):
        ListAdapters(harness["uow"], DenyAllAuth()).execute(
            ListAdaptersQuery(actor=harness["actor"])
        )
    with pytest.raises(AuthorizationError):
        ListGraders(harness["uow"], DenyAllAuth()).execute(
            ListGradersQuery(actor=harness["actor"])
        )


def test_get_run_events_artifacts_scores(run_world):
    run = CreateRun(
        run_world["uow"],
        run_world["ids"],
        run_world["auth"],
        run_world["events"],
        run_world["queue"],
        run_world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=run_world["actor"],
            project_id=run_world["project_id"],
            case_id=run_world["case_id"],
            case_version_id=run_world["case_version_id"],
            prompt_version_id=run_world["prompt_version_id"],
            agent_id=run_world["agent_id"],
            agent_version_id=run_world["agent_version_id"],
            adapter_version_id=run_world["adapter_version_id"],
            grader_version_refs=(
                (run_world["grader_id"], run_world["grader_version_id"]),
            ),
            platform_version_id="platform-1.0.0",
        )
    )
    StartRun(run_world["uow"], run_world["auth"], run_world["events"]).execute(
        StartRunCommand(actor=run_world["actor"], run_id=run.id, sandbox_id="sb-1")
    )
    RecordArtifact(
        run_world["uow"], run_world["ids"], run_world["auth"], run_world["events"]
    ).execute(
        RecordArtifactCommand(
            actor=run_world["actor"],
            run_id=run.id,
            kind="log",
            storage_key="runs/r/log.txt",
            content_type="text/plain",
            size_bytes=12,
            checksum="abc",
            artifact_id="art-1",
        )
    )
    RecordExecutionEvent(
        run_world["uow"], run_world["auth"], run_world["events"]
    ).execute(
        RecordExecutionEventCommand(
            actor=run_world["actor"],
            run_id=run.id,
            execution_event_id="evt-1",
            action={"kind": "message", "role": "assistant", "content_summary": "hi"},
            artifact_ids=("art-1",),
        )
    )
    StartGrading(run_world["uow"], run_world["auth"], run_world["events"]).execute(
        StartGradingCommand(actor=run_world["actor"], run_id=run.id)
    )
    RecordScore(
        run_world["uow"], run_world["ids"], run_world["auth"], run_world["events"]
    ).execute(
        RecordScoreCommand(
            actor=run_world["actor"],
            run_id=run.id,
            grader_id=run_world["grader_id"],
            grader_version_id=run_world["grader_version_id"],
            passed=True,
            numeric=1.0,
        )
    )

    events = GetRunEvents(run_world["uow"], run_world["auth"]).execute(
        GetRunEventsQuery(actor=run_world["actor"], run_id=run.id)
    )
    artifacts = GetRunArtifacts(run_world["uow"], run_world["auth"]).execute(
        GetRunArtifactsQuery(actor=run_world["actor"], run_id=run.id)
    )
    scores = GetRunScores(run_world["uow"], run_world["auth"]).execute(
        GetRunScoresQuery(actor=run_world["actor"], run_id=run.id)
    )

    assert len(events) == 1
    assert events[0].id == "evt-1"
    assert events[0].kind == "message"
    assert events[0].action["kind"] == "message"
    assert events[0].artifact_ids == ("art-1",)

    assert len(artifacts) == 1
    assert artifacts[0].id == "art-1"
    assert artifacts[0].kind == "log"
    assert artifacts[0].storage_key == "runs/r/log.txt"

    assert len(scores) == 1
    assert scores[0].value.passed is True
    assert scores[0].value.numeric == 1.0


def test_get_run_events_not_found(harness):
    with pytest.raises(NotFoundApplicationError):
        GetRunEvents(harness["uow"], harness["auth"]).execute(
            GetRunEventsQuery(actor=harness["actor"], run_id="missing")
        )
