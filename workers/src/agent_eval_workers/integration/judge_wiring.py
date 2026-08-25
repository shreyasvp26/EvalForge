"""Optional production rubric/judge wiring for the worker process.

Judge support is opt-in via ``JUDGE_PROVIDER``. Objective evaluations never
require a judge. When a rubric grader is pinned and no judge is configured,
``PinBasedGraderResolver`` continues to fail closed with an actionable reason.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from agent_eval_graders.providers.selection import create_judge_provider
from agent_eval_graders.rubric import RubricGrader, parse_rubric_specification
from agent_eval_graders.rubric.ports import JudgeProvider
from agent_eval_graders.sdk.grader import Grader
from agent_eval_shared.log import get_logger

logger = get_logger(__name__)

GraderFactory = Callable[[], Grader]


def detect_judge_provider_name(
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve configured judge provider name, or None when unset.

    Explicit ``JUDGE_PROVIDER`` wins. Otherwise auto-detect from available
    credentials (groq → anthropic → openai → gemini). Auto-detect never
    invents a provider without credentials.
    """
    env = environ if environ is not None else os.environ
    explicit = (env.get("JUDGE_PROVIDER") or "").strip().lower()
    if explicit:
        if explicit in {"none", "off", "disabled", "0", "false"}:
            return None
        return explicit

    if (env.get("GROQ_API_KEY") or env.get("GRAQ_API_KEY") or "").strip():
        return "groq"
    if (env.get("ANTHROPIC_API_KEY") or "").strip():
        return "anthropic"
    if (env.get("OPENAI_API_KEY") or "").strip():
        return "openai"
    if (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or "").strip():
        return "gemini"
    return None


def build_judge_provider(
    *,
    environ: Mapping[str, str] | None = None,
    provider_name: str | None = None,
) -> JudgeProvider | None:
    """Construct a judge provider when configured; otherwise return None."""
    name = (
        provider_name
        if provider_name is not None
        else detect_judge_provider_name(environ=environ)
    )
    if name is None:
        return None
    try:
        provider = create_judge_provider(name, environ=environ)
    except ValueError as exc:
        raise LookupError(
            f"Rubric grader requires a configured judge provider: {exc}"
        ) from exc
    logger.info("judge_provider_configured", provider=name)
    return provider


def make_rubric_factory(
    provider: JudgeProvider,
) -> Callable[[str, str, str], GraderFactory]:
    """Build PinBasedGraderResolver.rubric_factory from a live judge provider."""

    def rubric_factory(name: str, specification: str, label: str) -> GraderFactory:
        del label
        try:
            rubric = parse_rubric_specification(specification, default_title=name)
        except ValueError as exc:
            raise LookupError(
                f"Pinned rubric grader {name!r} has invalid specification: {exc}"
            ) from exc

        def factory() -> Grader:
            return RubricGrader(rubric=rubric, provider=provider, name=name or "rubric")

        return factory

    return rubric_factory
