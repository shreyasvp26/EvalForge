"""Versioned API root."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("")
def api_root() -> dict[str, str]:
    """Version marker for the Control Plane API surface."""
    return {
        "api_version": "v1",
        "status": "ok",
        "message": "EvalForge Control Plane REST API",
    }
