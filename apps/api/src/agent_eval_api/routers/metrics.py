"""Prometheus scrape endpoint — operational, unauthenticated."""

from __future__ import annotations

from agent_eval_shared.metrics import metrics_content_type, render_metrics
from fastapi import APIRouter, Response

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    """Expose Prometheus text exposition format."""
    return Response(content=render_metrics(), media_type=metrics_content_type())
