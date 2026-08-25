# EvalForge calculator-fix (canonical Phase 5 evaluation target)

Minimal public repository for live Gemini coding-agent evaluation.

## Task

Fix `calculator.add` so that `add(2, 3) == 5`. Do not modify `tests/test_calculator.py`.

## Layout

```
calculator.py
tests/test_calculator.py
```

Before the fix, `pytest` fails. After a correct agent edit, `pytest` passes.

## Publishing

This directory is the source for the public GitHub repository
`shreyasvp26/evalforge-calculator-fix`. EvalForge pins an exact commit SHA from
that repository when launching live evaluations.
