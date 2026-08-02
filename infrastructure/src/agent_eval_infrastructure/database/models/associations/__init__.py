"""Association persistence models."""

from agent_eval_infrastructure.database.models.associations.case_grader import (
    CaseGraderDeclarationOrm,
)
from agent_eval_infrastructure.database.models.associations.suite_composition import (
    SuiteCompositionOrm,
)

__all__ = ["CaseGraderDeclarationOrm", "SuiteCompositionOrm"]
