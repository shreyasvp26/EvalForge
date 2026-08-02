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
    claude_code/         # Claude Code stream-json
    cursor/              # Cursor Agent stream-json
    codex/               # OpenAI Codex CLI --json
    gemini/              # Gemini CLI stream-json
    aider/               # Aider structured NDJSON
  tests/                 # Mocked Sandbox / stream-source integration tests
```

## Lifecycle

`initialize` → `prepare` → `start` → `stream` → `finish` → `cleanup`

Every invocation is stateless. `run_adapter()` creates a fresh emitter and
lifecycle driver per call. Cancellation and timeout are checked between
streamed lines — malformed output becomes an ERROR observation and never
crashes the adapter.

## Event emission

`EventEmitter` reports through `EventSink` ports only — never repositories.
Guarantees ordered emission and exactly-once per `event_id` / `artifact_id`
within one invocation.

## Production adapters

| Adapter     | Binary   | Invocation highlights                     |
| ----------- | -------- | ----------------------------------------- |
| Claude Code | `claude` | `--print --output-format stream-json`     |
| Cursor      | `agent`  | `--print --output-format stream-json`     |
| Codex CLI   | `codex`  | `exec --json <prompt>`                    |
| Gemini CLI  | `gemini` | `--output-format stream-json`             |
| Aider       | `aider`  | `--yes --no-gitignore --message <prompt>` |

Each adapter:

- Implements the full SDK lifecycle
- Translates native NDJSON into existing `ObservationKind` values only
  (tool calls, stdout/stderr, file edits, messages, shell, completion, errors)
- Supports injectable `stream_source` for tests (no live CLI required)
- Accepts `cli_binary`, `extra_args`, environment, working directory, and
  timeouts via `ExecutionContext` / constructor knobs

```python
from agent_eval_adapters.cursor import CursorAdapter
from agent_eval_adapters.codex import CodexAdapter
from agent_eval_adapters.gemini import GeminiAdapter
from agent_eval_adapters.aider import AiderAdapter
from agent_eval_adapters.sdk import run_adapter

result = run_adapter(CursorAdapter(), context, sink)
```

## Tests

```bash
uv run pytest adapters/tests
```

Uses mocked Sandbox + injected stream sources only — no Workers, Graders, or
installed agent CLIs.
