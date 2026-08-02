"""Persistence ORM models — Infrastructure only.

Organized by Schema Design entity groups / Domain bounded contexts.
Importing this package registers every model on ``Base.metadata``.
"""

from agent_eval_infrastructure.auth.identity import UserOrm
from agent_eval_infrastructure.auth.membership import ProjectMembershipOrm
from agent_eval_infrastructure.database.models.agent_integration import (
    AdapterOrm,
    AdapterVersionOrm,
    AgentOrm,
    AgentVersionOrm,
)
from agent_eval_infrastructure.database.models.associations import (
    CaseGraderDeclarationOrm,
    SuiteCompositionOrm,
)
from agent_eval_infrastructure.database.models.evaluation_management import (
    CaseOrm,
    CaseVersionOrm,
    ProjectOrm,
    PromptOrm,
    PromptVersionOrm,
    SuiteOrm,
    SuiteVersionOrm,
)
from agent_eval_infrastructure.database.models.execution import (
    ArtifactOrm,
    ExecutionEventOrm,
    RunOrm,
    ScoreOrm,
)
from agent_eval_infrastructure.database.models.grading import (
    GraderOrm,
    GraderVersionOrm,
)
from agent_eval_infrastructure.database.models.platform import AuditLogOrm

__all__ = [
    "AdapterOrm",
    "AdapterVersionOrm",
    "AgentOrm",
    "AgentVersionOrm",
    "ArtifactOrm",
    "AuditLogOrm",
    "CaseGraderDeclarationOrm",
    "CaseOrm",
    "CaseVersionOrm",
    "ExecutionEventOrm",
    "GraderOrm",
    "GraderVersionOrm",
    "ProjectMembershipOrm",
    "ProjectOrm",
    "PromptOrm",
    "PromptVersionOrm",
    "RunOrm",
    "ScoreOrm",
    "SuiteCompositionOrm",
    "SuiteOrm",
    "SuiteVersionOrm",
    "UserOrm",
]
