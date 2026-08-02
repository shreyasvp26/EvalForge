"""OpenTelemetry tracing facade (System Overview §12 — initial cut).

Configure once at process start. Spans are no-ops when tracing is disabled.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import Tracer

_configured = False
_provider: TracerProvider | None = None


def configure_tracing(
    *,
    enabled: bool = False,
    service_name: str = "evalforge",
    environment: str = "development",
    otlp_endpoint: str | None = None,
    force: bool = False,
) -> None:
    """Install a process-wide TracerProvider.

    When ``enabled`` is false, uses the global no-op provider.
    When ``otlp_endpoint`` is set, exports via OTLP/HTTP; otherwise uses a
    console exporter only outside production (dev visibility).
    """
    global _configured, _provider
    if _configured and not force:
        return

    if not enabled:
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        _provider = None
        _configured = True
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": environment,
        }
    )
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif environment != "production":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider = provider
    _configured = True


def get_tracer(name: str) -> Tracer:
    """Return a tracer for ``name`` (safe before configure — no-op provider)."""
    return trace.get_tracer(name)


def start_span(
    name: str,
    *,
    tracer_name: str = "evalforge",
    attributes: dict[str, Any] | None = None,
) -> AbstractContextManager[trace.Span]:
    """Start a span context manager."""
    tracer = get_tracer(tracer_name)
    return tracer.start_as_current_span(name, attributes=attributes or {})


def shutdown_tracing() -> None:
    """Flush and shut down the configured provider (process exit)."""
    global _configured, _provider
    if _provider is not None:
        _provider.shutdown()
    _provider = None
    _configured = False
