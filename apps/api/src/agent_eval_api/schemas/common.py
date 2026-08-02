"""Shared Pydantic schemas for the Control Plane API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class CollectionResponse[T](BaseModel):
    """List wrapper — cursor pagination metadata can be added later."""

    model_config = ConfigDict(extra="forbid")

    items: list[T]
    count: int


def idempotency_header_field() -> Any:
    return Field(
        default=None,
        validation_alias="Idempotency-Key",
        description="Optional client idempotency key for safe POST retries",
    )
