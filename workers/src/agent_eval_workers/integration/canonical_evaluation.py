"""Canonical Phase 5 live evaluation targets (public repository pins)."""

from __future__ import annotations

# Public repository used for live Gemini Docker proof.
# Source lives in evaluations/canonical/calculator-fix/ in this monorepo.
CANONICAL_CALCULATOR_REPO = (
    "https://github.com/shreyasvp26/evalforge-calculator-fix.git"
)
# Updated after publishing the initial broken implementation commit.
CANONICAL_CALCULATOR_BROKEN_SHA = "b8db052ac9c1d67b0836a637df69660c5f4f3554"

CANONICAL_CALCULATOR_PROMPT = (
    "Fix the add function in calculator.py so that add(2, 3) returns 5. "
    "Do not modify tests/test_calculator.py. "
    "Verify with: python3 -m pytest tests/ -q"
)
