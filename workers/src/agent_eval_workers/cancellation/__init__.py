"""Cancellation — cooperative stop signals for in-flight Runs.

Responsibility (Execution Engine Architecture — cancellation / terminal paths):
- Observe cancellation requests for a claimed Run
- Propagate cancellation into Engine lifecycle so the Run reaches Cancelled
- Distinguish cancellation from infrastructure failure and Agent task failure

Must NOT:
- Silently drop Execution Events already recorded
- Bypass Application when recording the terminal Cancelled transition
- Own Adapter-internal interrupt mechanisms (Adapter port may expose a hook)
- Mutate Domain Run status directly
"""

from agent_eval_workers.cancellation.ports import CancellationPort
from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry

__all__ = [
    "CancellationPort",
    "InMemoryCancellationRegistry",
]
