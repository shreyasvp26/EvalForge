"""Objective tests for calculator.add — do not modify for the evaluation task."""

from calculator import add


def test_add_returns_sum() -> None:
    assert add(2, 3) == 5
