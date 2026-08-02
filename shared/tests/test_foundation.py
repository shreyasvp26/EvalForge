from __future__ import annotations

import pytest
from agent_eval_shared import (
    ApplicationError,
    ConfigurationError,
    InfrastructureError,
    bind_context,
    clear_context,
    create_correlation_id,
    get_context,
    load_settings,
    serialize_error,
)
from agent_eval_shared.config import BaseSettings


def test_create_correlation_id_is_uuid_shaped() -> None:
    value = create_correlation_id()
    assert len(value) == 36
    assert value.count("-") == 4


def test_serialize_typed_error() -> None:
    error = InfrastructureError(
        "db down",
        code="DB_UNAVAILABLE",
        retryable=True,
        details={"host": "db"},
    )
    payload = serialize_error(error)
    assert payload["code"] == "DB_UNAVAILABLE"
    assert payload["retryable"] is True
    assert payload["details"] == {"host": "db"}


def test_application_error_defaults_not_retryable() -> None:
    error = ApplicationError("nope", code="FORBIDDEN")
    assert error.retryable is False


def test_bind_and_clear_context() -> None:
    clear_context()
    bind_context(correlation_id="abc", run_id="run-1")
    assert get_context()["correlation_id"] == "abc"
    clear_context()
    assert get_context() == {}


def test_load_settings_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "not-a-level")
    with pytest.raises(ConfigurationError):
        load_settings(BaseSettings)
