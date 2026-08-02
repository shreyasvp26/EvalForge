# EvalForge Grader Layer

Reads a completed Run's Execution Events and Artifacts and produces immutable
Scores. Depends only on Domain + Shared (+ `httpx` for production judge
providers).

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
    rubric/              # LLM-as-judge rubric family
      models.py          # RubricSpecification, JudgePrompt, ParsedJudgment
      ports.py           # JudgeProvider / PromptBuilder / ResponseParser
      prompt_builder.py  # Prompt from Run record + pinned rubric only
      judge.py           # MockJudgeProvider (injectable; no vendor APIs)
      runner.py          # RubricGrader + JudgeRunner
      response_parser.py # Strict JSON schema validation
      exceptions.py / registry.py
    providers/           # Production JudgeProvider plugins (Phase 12)
      errors.py          # Auth / rate-limit / network / invalid-response
      retry.py           # Exponential backoff (retryable only)
      config.py          # Shared knobs + env loading
      http.py            # HTTP status → platform failure mapping
      selection.py       # create_judge_provider("anthropic"|"openai"|"gemini")
      anthropic/         # Messages API
      openai/            # Chat Completions API
      gemini/            # generateContent API
```

## Lifecycle

**Shared (both families):**
`initialize` → `read_run` → `grade` → `produce_scores` → `cleanup`

**Rubric-internal (inside `grade`):**
`build_prompt` → `invoke_judge` → `parse_response`

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

## Rubric graders

`RubricGrader` performs structured qualitative evaluation via an injectable
`JudgeProvider`. Production providers (Anthropic, OpenAI, Gemini) implement
the same port as `MockJudgeProvider` — the Grader lifecycle is unchanged.

### Prompt construction

Prompts are built **only** from:

- Execution Events (NDM)
- Artifact metadata (no repository fetches)
- Run metadata
- Pinned Grader Version + immutable `RubricSpecification`

Never from other Runs, other Scores, or external context. Run content is
treated as untrusted data (instruction-injection posture).

### Judge abstraction

`JudgeProvider.complete(JudgeRequest) -> JudgeRawResponse` is injectable.
`DeterminismControls` (temperature / seed / model_hint) minimize variance;
rubric grading remains bounded-variance, not bit-identical.

### Production judge providers

| Provider  | Env key             | Default model              | Seed |
| --------- | ------------------- | -------------------------- | ---- |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | no   |
| OpenAI    | `OPENAI_API_KEY`    | `gpt-4o`                   | yes  |
| Gemini    | `GEMINI_API_KEY`    | `gemini-2.0-flash`         | yes  |

Shared knobs (per-vendor prefix, e.g. `ANTHROPIC_TIMEOUT_SECONDS`):

- timeout, retry count, temperature, seed, max tokens, optional base URL

```python
from agent_eval_graders.providers import create_judge_provider
from agent_eval_graders.rubric import RubricGrader

provider = create_judge_provider("anthropic")  # reads ANTHROPIC_API_KEY
grader = RubricGrader(rubric=rubric, provider=provider)
```

Effective temperature / seed / model are recorded on `JudgeRawResponse.metadata`
and flow into Score detail via the existing parser / `produce_scores` path.

### Response parsing

Strict JSON schema: `numeric` and/or `passed`, required `reason`, optional
criteria breakdown + metadata. Malformed JSON or schema mismatch →
judgment failure (`RubricParseError` / `RubricSchemaError`), not a Score.

### Failure model

| Failure                   | Class                       | Retryable |
| ------------------------- | --------------------------- | --------- |
| Judge timeout             | `JudgeTimeout`              | yes       |
| Provider unavailable      | `JudgeProviderUnavailable`  | yes       |
| Rate limited (HTTP 429)   | `JudgeRateLimitError`       | yes       |
| Network / transport       | `JudgeNetworkError`         | yes       |
| Authentication            | `JudgeAuthenticationError`  | no        |
| Invalid vendor payload    | `JudgeInvalidResponseError` | no        |
| Invalid JSON / schema     | `RubricParseError` / Schema | no        |
| Prompt construction error | `RubricPromptError`         | no        |

Vendor exceptions never leave the provider package. Retry uses exponential
backoff and skips non-retryable failures (auth, invalid response, schema).

Failures stay isolated to that Grader Version; siblings still produce Scores
(partial grading).

## Score model

Produces Domain `Score` + `ScoreValue` (`passed` / `numeric` / `categorical` +
`detail.reason`), attributed to the pinned Grader Version, with timestamps.
Rubric Scores also carry criteria breakdown, rubric fingerprint, and
determinism controls in detail/metadata.

## Tests

```bash
uv run pytest graders/tests
```

Rubric unit tests use `MockJudgeProvider`. Provider integration tests use
mocked HTTP (`httpx.MockTransport`) only — they never call an external LLM.
