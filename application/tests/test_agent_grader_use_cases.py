"""Agent, Adapter, and Grader use-case orchestration tests."""

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
from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_domain.common.ids import AgentId
from fakes import (
    AllowAllAuth,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    SharedStore,
)


@pytest.fixture
def harness():
    store = SharedStore()
    return {
        "uow": InMemoryUnitOfWorkFactory(store),
        "ids": InMemoryIdGenerator("x"),
        "auth": AllowAllAuth(),
        "events": RecordingEventDispatcher(),
        "actor": Actor(id="user-1"),
        "store": store,
    }


def test_agent_adapter_connect_and_publish(harness):
    agent = CreateAgent(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(CreateAgentCommand(actor=harness["actor"], name="Claude Code"))

    adapter = CreateAdapter(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateAdapterCommand(
            actor=harness["actor"],
            agent_id=agent.id,
            name="Claude Adapter",
        )
    )
    assert adapter.agent_id == agent.id

    reloaded = harness["store"].agents.get(AgentId(agent.id))
    assert reloaded.adapter_id is not None
    assert reloaded.adapter_id.value == adapter.id

    av = CreateAgentDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateAgentDraftVersionCommand(
            actor=harness["actor"], agent_id=agent.id, label="1.0.0"
        )
    )
    published_av = PublishAgentVersion(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(
        PublishAgentVersionCommand(
            actor=harness["actor"], agent_id=agent.id, version_id=av.id
        )
    )
    assert published_av.status == "active"

    adv = CreateAdapterDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateAdapterDraftVersionCommand(
            actor=harness["actor"], adapter_id=adapter.id, label="1.0.0"
        )
    )
    published_adv = PublishAdapterVersion(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(
        PublishAdapterVersionCommand(
            actor=harness["actor"], adapter_id=adapter.id, version_id=adv.id
        )
    )
    assert published_adv.status == "active"


def test_grader_create_and_publish(harness):
    grader = CreateGrader(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateGraderCommand(
            actor=harness["actor"],
            name="Tests Pass",
            family="objective",
        )
    )
    draft = CreateGraderDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateGraderDraftVersionCommand(
            actor=harness["actor"],
            grader_id=grader.id,
            label="v1",
            specification="pytest exit 0",
        )
    )
    published = PublishGraderVersion(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(
        PublishGraderVersionCommand(
            actor=harness["actor"],
            grader_id=grader.id,
            version_id=draft.id,
        )
    )
    assert published.status == "active"
