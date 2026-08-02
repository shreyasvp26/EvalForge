# EvalForge Grader Layer

Reads a completed Run's Execution Events and Artifacts and produces immutable
Scores. Depends only on Domain + Shared.

This package does **not** execute code, orchestrate Runs, or persist Scores.

## Layout

```
graders/
  src/agent_eval_graders/
    sdk/                 # Shared Grader runtime
      grader.py          # Grader / BaseGrader contract
      context.py         # Immutable GradingContext
      lifecycle.py       # initialize→read_run→grade→produce_scores→cleanup
      execution.py       # run_grader / run_graders_isolated
      registry.py
      models.py / ports.py / exceptions.py
    objective/           # Deterministic objective graders
      build_success.py
      exit_code.py
      test_pass.py
      lint.py
      expected_file.py
      diff_validation.py
      json_output.py
```

## Lifecycle

`initialize` → `read_run` → `grade` → `produce_scores` → `cleanup`

Each invocation is stateless and isolated. Sibling grader failures never
affect each other (`run_graders_isolated`).

## Objective graders

| Grader               | Signal                          |
| -------------------- | ------------------------------- |
| BuildSuccessGrader   | Build command exit codes        |
| ExitCodeGrader       | Configurable shell exit code    |
| TestPassGrader       | Test-runner exit codes          |
| LintGrader           | Linter exit codes               |
| ExpectedFileGrader   | Required file-edit paths        |
| DiffValidationGrader | Edit presence / path allow-deny |
| JSONOutputGrader     | Valid JSON in recorded stdout   |

## Score model

Produces Domain `Score` + `ScoreValue` (`passed` / `numeric` / `categorical` +
`detail.reason`), attributed to the pinned Grader Version, with timestamps.

## Tests

```bash
uv run pytest graders/tests
```
