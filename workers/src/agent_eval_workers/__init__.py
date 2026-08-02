"""EvalForge Background Workers / Execution Runtime.

Thin chassis that hosts the Execution Engine and sequences Application calls
(Backend Architecture §4 / §7; Execution Engine Architecture).

This package must remain thin: it orchestrates, it does not contain Adapter
translation, Grader judgment, or Domain invariants.
"""

from __future__ import annotations

__all__: list[str] = []
