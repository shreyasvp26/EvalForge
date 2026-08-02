# EvalForge Sandbox Runtime

Isolated execution component. Provisions Docker containers, mounts
repositories, injects environment, enforces resource limits, runs commands,
collects stdout/stderr/artifacts, and always cleans up.

This package does **not** orchestrate Runs, translate agent output, or grade
results (see Execution Engine Architecture — Sandbox Lifecycle).

## Layout

```
sandbox/
  src/agent_eval_sandbox/
    ports.py          # SandboxRuntime + DockerEngine contracts
    models.py         # Spec / handle / execution / artifact types
    exceptions.py     # Infrastructure-class sandbox errors
    manager.py        # Handle registry + session cleanup guarantees
    docker/
      sandbox.py      # DockerSandbox (SandboxRuntime)
      lifecycle.py    # create / start / stop / destroy
      executor.py     # execute + timeout + resource usage
      mounts.py       # bind mounts (incl. readonly)
      networking.py   # default-deny network policy
      resources.py    # CPU / memory / disk host config
      cleanup.py      # ensure_destroyed / cleanup guards
      engine.py       # docker-py adapter
  tests/              # FakeDockerEngine unit tests (+ optional live Docker)
```

## API

```python
from agent_eval_sandbox import (
    DockerSandbox,
    DockerPyEngine,
    SandboxManager,
    SandboxSpec,
    ExecutionRequest,
    ResourceLimits,
    NetworkPolicy,
    NetworkMode,
)

engine = DockerPyEngine.from_env()  # or inject a fake in tests
manager = SandboxManager(runtime=DockerSandbox(engine=engine))

with manager.session(SandboxSpec(image="busybox:1.36")) as handle:
    result = manager.execute(handle, ExecutionRequest(command=("echo", "hi")))
    # result.exit_code / stdout / stderr / duration_seconds / resource_usage
```

Interfaces: `create` → `start` → `execute` / `copy_out` → `stop` → `destroy`.

## Resource limits

| Dimension       | Enforcement                                 |
| --------------- | ------------------------------------------- |
| CPU             | Docker `NanoCpus`                           |
| Memory          | Docker `Memory` (+ swap capped)             |
| Disk            | Best-effort `StorageOpt.size`               |
| Timeout         | In-container `timeout` + host-side deadline |
| Working dir     | Container `working_dir`                     |
| Readonly mounts | Bind mounts with `ReadOnly=True`            |
| Network         | Default `NetworkMode.NONE` (deny-all)       |

## Cleanup

`SandboxManager.session` and `docker.cleanup.ensure_destroyed` always tear down
containers after timeout, failure, or interruption. `cleanup_all()` force-
destroys every tracked handle.

## Tests

```bash
uv run pytest sandbox/tests                # mocked Docker (default)
uv run pytest sandbox/tests -m integration # requires live Docker daemon
```

## Dependencies

- `agent-eval-shared` only (errors). **Must not** import Domain, Application,
  Workers, Adapters, or Graders.
