"""Agent and Adapter DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.agent_integration.adapter import Adapter, AdapterVersion
from agent_eval_domain.agent_integration.agent import Agent, AgentVersion


@dataclass(frozen=True, slots=True)
class AgentVersionDTO:
    id: str
    agent_id: str
    version_number: int
    status: str
    label: str
    release_notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: AgentVersion) -> AgentVersionDTO:
        return cls(
            id=version.id.value,
            agent_id=version.agent_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            label=version.label,
            release_notes=version.release_notes,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class AgentDTO:
    id: str
    name: str
    description: str
    adapter_id: str | None
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: tuple[AgentVersionDTO, ...]

    @classmethod
    def from_domain(cls, agent: Agent) -> AgentDTO:
        active = agent.active_version()
        return cls(
            id=agent.id.value,
            name=agent.name,
            description=agent.description,
            adapter_id=agent.adapter_id.value if agent.adapter_id else None,
            status=agent.status.value,
            created_at=agent.created_at,
            active_version_id=active.id.value if active else None,
            versions=tuple(AgentVersionDTO.from_domain(v) for v in agent.versions),
        )


@dataclass(frozen=True, slots=True)
class AdapterVersionDTO:
    id: str
    adapter_id: str
    version_number: int
    status: str
    label: str
    notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, version: AdapterVersion) -> AdapterVersionDTO:
        return cls(
            id=version.id.value,
            adapter_id=version.adapter_id.value,
            version_number=version.version_number.value,
            status=version.status.value,
            label=version.label,
            notes=version.notes,
            predecessor_version_id=(
                version.predecessor_version_id.value
                if version.predecessor_version_id
                else None
            ),
            created_at=version.created_at,
        )


@dataclass(frozen=True, slots=True)
class AdapterDTO:
    id: str
    agent_id: str
    name: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: tuple[AdapterVersionDTO, ...]

    @classmethod
    def from_domain(cls, adapter: Adapter) -> AdapterDTO:
        active = adapter.active_version()
        return cls(
            id=adapter.id.value,
            agent_id=adapter.agent_id.value,
            name=adapter.name,
            status=adapter.status.value,
            created_at=adapter.created_at,
            active_version_id=active.id.value if active else None,
            versions=tuple(AdapterVersionDTO.from_domain(v) for v in adapter.versions),
        )
