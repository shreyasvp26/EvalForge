"""Canonical benchmark catalog definitions (immutable pins)."""

from __future__ import annotations

from dataclasses import dataclass

CODING_BENCHMARK_V1_REPO = (
    "https://github.com/shreyasvp26/evalforge-coding-benchmark-v1.git"
)
CODING_BENCHMARK_V1_SHA = "47329c4885c2855072b15aaee227f5b92416301f"

CANONICAL_CALCULATOR_REPO = (
    "https://github.com/shreyasvp26/evalforge-calculator-fix.git"
)
CANONICAL_CALCULATOR_BROKEN_SHA = "b8db052ac9c1d67b0836a637df69660c5f4f3554"

CANONICAL_CALCULATOR_PROMPT = (
    "Fix the add function in calculator.py so that add(2, 3) returns 5. "
    "Do not modify tests/test_calculator.py. "
    "Verify with: python3 -m pytest tests/ -q"
)

WORKSPACE_PYTEST_SPEC = "workspace:python3 -m pytest tests/ -q"


@dataclass(frozen=True, slots=True)
class CodingBenchmarkTask:
    case_key: str
    title: str
    description: str
    subdirectory: str
    category: str
    difficulty: str
    prompt: str
    tags: tuple[str, ...]


CODING_BENCHMARK_V1_TASKS: tuple[CodingBenchmarkTask, ...] = (
    CodingBenchmarkTask(
        case_key="01-calculator-add",
        title="Fix arithmetic bug",
        description="Repair calculator.add so add(2, 3) == 5 without changing tests.",
        subdirectory="tasks/01-calculator-add",
        category="bugfix",
        difficulty="easy",
        prompt=(
            "Fix the add function in calculator.py so that add(2, 3) returns 5. "
            "Do not modify tests/test_calculator.py. "
            "Verify with: python3 -m pytest tests/ -q"
        ),
        tags=("python", "pytest", "arithmetic"),
    ),
    CodingBenchmarkTask(
        case_key="02-fibonacci",
        title="Fix Fibonacci off-by-one",
        description="Correct fib(n) so the 0-indexed Fibonacci sequence matches tests.",
        subdirectory="tasks/02-fibonacci",
        category="bugfix",
        difficulty="easy",
        prompt=(
            "Fix fibonacci.fib so it returns the correct 0-indexed Fibonacci number. "
            "Do not modify tests/test_fibonacci.py. "
            "Verify with: python3 -m pytest tests/ -q"
        ),
        tags=("python", "pytest", "off-by-one"),
    ),
    CodingBenchmarkTask(
        case_key="03-merge-dicts",
        title="Implement dict merge",
        description="Shallow-merge two dictionaries with right-hand precedence.",
        subdirectory="tasks/03-merge-dicts",
        category="feature",
        difficulty="easy",
        prompt=(
            "Implement merge(left, right) so it shallow-merges dictionaries and "
            "right-hand values win on conflicts. Do not modify tests/test_merge.py. "
            "Verify with: python3 -m pytest tests/ -q"
        ),
        tags=("python", "pytest", "data-transform"),
    ),
    CodingBenchmarkTask(
        case_key="04-parse-csv",
        title="Fix CSV empty-field parsing",
        description="Preserve empty fields when splitting a simple CSV line.",
        subdirectory="tasks/04-parse-csv",
        category="edge-case",
        difficulty="medium",
        prompt=(
            "Fix parse_csv.parse_csv_line so empty fields are preserved "
            "(e.g. 'a,,c' -> ['a', '', 'c']). Do not modify tests/test_parse_csv.py. "
            "Verify with: python3 -m pytest tests/ -q"
        ),
        tags=("python", "pytest", "csv"),
    ),
    CodingBenchmarkTask(
        case_key="05-clamp",
        title="Fix clamp upper bound",
        description=(
            "Clamp values into an inclusive [lo, hi] range including the upper bound."
        ),
        subdirectory="tasks/05-clamp",
        category="bugfix",
        difficulty="easy",
        prompt=(
            "Fix clamp.clamp so values above hi return hi. "
            "Do not modify tests/test_clamp.py. "
            "Verify with: python3 -m pytest tests/ -q"
        ),
        tags=("python", "pytest", "boundaries"),
    ),
)
