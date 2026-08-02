"""Normalized Domain Model action serialization for Execution Event payloads.

Re-exports Domain codecs so Infrastructure mappers keep a stable import path.
"""

from __future__ import annotations

from agent_eval_domain.execution.ndm_codec import action_from_payload, action_to_payload

__all__ = ["action_from_payload", "action_to_payload"]
