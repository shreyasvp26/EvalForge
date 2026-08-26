"""Gated OmniRoute live integration test (optional; never required for CI).

Enable with:

    EVALFORGE_OMNIROUTE_INTEGRATION=1
    OMNIROUTE_BASE_URL=...
    OMNIROUTE_API_KEY=...
    EVALFORGE_OMNIROUTE_MODEL=<exact-model-id>

Fails honestly when OmniRoute is unavailable. Never fabricates success.
"""

from __future__ import annotations

import os

import pytest
from agent_eval_application.gateways import (
    InferenceRequest,
    create_omniroute_gateway,
    load_omniroute_config,
)
from agent_eval_domain.execution.provider_runtime import ModelId, RoutingMode

pytestmark = pytest.mark.skipif(
    os.environ.get("EVALFORGE_OMNIROUTE_INTEGRATION", "").strip()
    not in {"1", "true", "yes"},
    reason="Set EVALFORGE_OMNIROUTE_INTEGRATION=1 to run OmniRoute integration",
)


def test_omniroute_explicit_model_round_trip() -> None:
    config = load_omniroute_config()
    assert config is not None, (
        "OmniRoute integration enabled but OMNIROUTE_BASE_URL / "
        "OMNIROUTE_API_KEY are not both configured"
    )
    model = (os.environ.get("EVALFORGE_OMNIROUTE_MODEL") or "").strip()
    assert model, "Set EVALFORGE_OMNIROUTE_MODEL to an exact model id"
    assert model.lower() != "auto", "Integration test requires an exact model pin"

    gateway = create_omniroute_gateway()
    assert gateway is not None
    try:
        response = gateway.complete(
            InferenceRequest(
                model=ModelId(model),
                messages=(
                    {
                        "role": "user",
                        "content": "Reply with exactly: ok",
                    },
                ),
                routing_mode=RoutingMode.FIXED,
                max_tokens=32,
            )
        )
    except Exception as exc:  # noqa: BLE001 — honest failure for unavailable gateway
        pytest.fail(f"OmniRoute request failed honestly: {exc}")

    assert response.requested_model == model
    # actual_model may be None if the gateway does not report it — do not fabricate.
    if response.actual_model is not None:
        assert response.actual_model.strip()
    assert "OMNIROUTE_API_KEY" not in str(response)
    secret = os.environ.get("OMNIROUTE_API_KEY", "")
    if secret:
        assert secret not in str(response)
        assert secret not in str(response.raw)
    assert response.gateway_key.value == "omniroute"
