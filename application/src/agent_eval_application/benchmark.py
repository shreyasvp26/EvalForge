"""Benchmark identity helpers — SuiteVersion is the immutable benchmark container.

EvalForge does not introduce a separate Benchmark aggregate. A published
``SuiteVersion`` (immutable case composition) plus pinned Prompt / Grader /
Platform versions already define a reproducible benchmark. Individual Runs
pin Agent / Adapter / execution_mode so the same benchmark can be evaluated
by different supported agents.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.dto.run import RunDTO


@dataclass(frozen=True, slots=True)
class BenchmarkIdentity:
    """Stable identity for the evaluation definition (agent-independent)."""

    suite_version_id: str | None
    case_version_id: str
    prompt_version_id: str
    platform_version_id: str
    grader_version_ids: tuple[str, ...]
    repository_url: str | None
    commit_sha: str | None
    benchmark_key: str
    """Opaque comparable key for exact definition matching."""


def benchmark_identity_from_run(
    dto: RunDTO,
    *,
    repository_url: str | None,
    commit_sha: str | None,
) -> BenchmarkIdentity:
    graders = tuple(sorted(dto.pins.grader_version_ids))
    suite = dto.pins.suite_version_id or ""
    key = "|".join(
        [
            suite,
            dto.pins.case_version_id,
            dto.pins.prompt_version_id,
            dto.pins.platform_version_id,
            ",".join(graders),
            (repository_url or "").strip(),
            (commit_sha or "").strip(),
        ]
    )
    return BenchmarkIdentity(
        suite_version_id=dto.pins.suite_version_id,
        case_version_id=dto.pins.case_version_id,
        prompt_version_id=dto.pins.prompt_version_id,
        platform_version_id=dto.pins.platform_version_id,
        grader_version_ids=graders,
        repository_url=repository_url,
        commit_sha=commit_sha,
        benchmark_key=key,
    )


# Dimensions that must match for cross-agent fair comparison.
BENCHMARK_COMPARABILITY_DIMENSIONS: tuple[str, ...] = (
    "case_version_id",
    "prompt_version_id",
    "platform_version_id",
    "grader_version_ids",
    "repository_url",
    "commit_sha",
)

# Dimensions expected to differ when comparing agents on the same benchmark.
AGENT_COMPARISON_DIMENSIONS: tuple[str, ...] = (
    "agent_version_id",
    "adapter_version_id",
    "adapter_key",
    "execution_mode",
)
