"""Resolve pinned Prompt Version content for Adapter execution."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListCasesByProjectQuery
from agent_eval_domain.common.ids import RunId
from agent_eval_shared.log import get_logger

logger = get_logger(__name__)

DEFAULT_PROMPT = "solve the case"


@dataclass(slots=True)
class PinnedPromptResolver:
    """Load the Run's pinned Prompt Version content via Application queries.

    Falls back to ``DEFAULT_PROMPT`` only when the pin cannot be resolved so
    deterministic/dev paths remain executable; production runs should always
    resolve a real prompt.
    """

    actor: Actor
    get_run: object
    list_cases: object
    fallback: str = DEFAULT_PROMPT

    def resolve(self, run_id: RunId) -> str:
        run = self.get_run.execute(  # type: ignore[attr-defined]
            GetRunQuery(actor=self.actor, run_id=run_id.value)
        )
        prompt_version_id = run.pins.prompt_version_id
        cases = self.list_cases.execute(  # type: ignore[attr-defined]
            ListCasesByProjectQuery(actor=self.actor, project_id=run.pins.project_id)
        )
        for case in cases:
            for version in case.prompt_versions:
                if version.id == prompt_version_id:
                    content = str(version.content).strip()
                    if content:
                        return content
                    logger.warning(
                        "pinned_prompt_empty",
                        run_id=run_id.value,
                        prompt_version_id=prompt_version_id,
                    )
                    return self.fallback
        logger.warning(
            "pinned_prompt_unresolved",
            run_id=run_id.value,
            prompt_version_id=prompt_version_id,
            project_id=run.pins.project_id,
        )
        return self.fallback
