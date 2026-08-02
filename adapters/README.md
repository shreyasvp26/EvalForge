# EvalForge Adapter Layer

Translates coding-agent native behavior into the Normalized Domain Model.

This package does **not** orchestrate, schedule, grade, or persist. It depends
only on Domain (NDM shapes), Shared, and Sandbox.

## Layout

```
adapters/
  src/agent_eval_adapters/
    sdk/                 # Adapter SDK (interfaces + shared runtime)
      adapter.py         # Adapter / BaseAdapter contract
      context.py         # Immutable ExecutionContext
      capabilities.py
      lifecycle.py       # initialize→prepare→start→stream→finish→cleanup
      emitter.py         # Ordered, exactly-once EventEmitter
      translator.py      # NativeObservation → NDM
      execution.py       # run_adapter() entry point
      models.py / ports.py / exceptions.py
    claude_code/         # First production Adapter
      adapter.py
      parser.py          # stream-json NDJSON → NativeObservation
  tests/                 # Mocked Sandbox integration tests
```

## Lifecycle

`initialize` → `prepare` → `start` → `stream` → `finish` → `cleanup`

Every invocation is stateless. `run_adapter()` creates a fresh emitter and
lifecycle driver per call.

## Event emission

`EventEmitter` reports through `EventSink` ports only — never repositories.
Guarantees ordered emission and exactly-once per `event_id` / `artifact_id`
within one invocation.

## Claude Code

```python
from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.sdk import run_adapter, ExecutionContext

result = run_adapter(ClaudeCodeAdapter(), context, sink)
```

Observes Claude Code `--output-format stream-json`, maps tool calls / edits /
shell / completion into NDM, and supports cancellation + timeout between
stream lines.

## Tests

```bash
uv run pytest adapters/tests
```

Uses mocked Sandbox only — no Workers, Graders, or live Claude CLI.
