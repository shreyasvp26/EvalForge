"""Read queries."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class GetProjectQuery:
    actor: Actor
    project_id: str


@dataclass(frozen=True, slots=True)
class ListProjectsQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class GetSuiteQuery:
    actor: Actor
    suite_id: str


@dataclass(frozen=True, slots=True)
class ListSuitesByProjectQuery:
    actor: Actor
    project_id: str


@dataclass(frozen=True, slots=True)
class GetCaseQuery:
    actor: Actor
    case_id: str


@dataclass(frozen=True, slots=True)
class ListCasesByProjectQuery:
    actor: Actor
    project_id: str


@dataclass(frozen=True, slots=True)
class GetRunQuery:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class ListRunsByProjectQuery:
    actor: Actor
    project_id: str


@dataclass(frozen=True, slots=True)
class GetRunEventsQuery:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class GetRunArtifactsQuery:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class GetRunScoresQuery:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class GetRunProvenanceQuery:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class GetAgentQuery:
    actor: Actor
    agent_id: str


@dataclass(frozen=True, slots=True)
class ListAgentsQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class GetAdapterQuery:
    actor: Actor
    adapter_id: str


@dataclass(frozen=True, slots=True)
class ListAdaptersQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class GetGraderQuery:
    actor: Actor
    grader_id: str


@dataclass(frozen=True, slots=True)
class ListGradersQuery:
    actor: Actor


@dataclass(frozen=True, slots=True)
class GetCurrentUserQuery:
    actor: Actor
