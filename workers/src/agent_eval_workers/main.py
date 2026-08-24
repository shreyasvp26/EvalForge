"""Background Worker process entry — claim loop over Redis.

Composition root for the Execution Plane process. Wires Infrastructure +
production LifecycleOrchestrator (Sandbox / Adapter / Graders / Application)
into ``WorkerRuntime`` without importing the API Layer.
"""

from __future__ import annotations

import os
import signal
import time
from typing import cast

from agent_eval_infrastructure import RuntimeProfile, build_infrastructure
from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue
from agent_eval_shared.config import Environment, LogLevel
from agent_eval_shared.log import configure_logging, get_logger
from agent_eval_shared.metrics import configure_metrics
from agent_eval_shared.tracing import configure_tracing, shutdown_tracing
from redis import Redis

from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.queue_redis import RedisWorkerQueue

logger = get_logger("agent_eval_workers.main")


def run() -> None:
    """CLI entry: ``evalforge-worker``."""
    environment = cast(Environment, os.environ.get("ENVIRONMENT", "production"))
    log_level = cast(LogLevel, os.environ.get("LOG_LEVEL", "info"))
    worker_id = os.environ.get("WORKER_ID", "worker-1")

    configure_logging(
        level=log_level,
        environment=environment,
        service_name="evalforge-worker",
    )
    configure_metrics(enabled=os.environ.get("METRICS_ENABLED", "true") != "false")
    configure_tracing(
        enabled=os.environ.get("TRACING_ENABLED", "false") == "true",
        service_name="evalforge-worker",
        environment=environment,
        otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
    )

    infra = build_infrastructure(profile=RuntimeProfile.PRODUCTION)
    redis_url = os.environ.get("REDIS_URL", infra.settings.redis_url)
    client = Redis.from_url(redis_url, decode_responses=True)
    run_queue = RedisRunQueue(
        client,
        key_prefix=os.environ.get(
            "RUN_QUEUE_KEY_PREFIX", infra.settings.run_queue_key_prefix
        ),
        claim_timeout_seconds=float(
            os.environ.get(
                "RUN_QUEUE_CLAIM_TIMEOUT_SECONDS",
                str(infra.settings.run_queue_claim_timeout_seconds),
            )
        ),
    )
    worker_queue = RedisWorkerQueue(run_queue)

    timeout_raw = os.environ.get("WORKER_EXECUTION_TIMEOUT_SECONDS")
    execution_timeout = float(timeout_raw) if timeout_raw else None

    bundle = build_production_worker(
        queue=worker_queue,
        uow_factory=infra.uow_factory,
        ids=infra.ids,
        events=infra.events,
        worker_id=worker_id,
        execution_timeout_seconds=execution_timeout,
    )
    worker = bundle.worker

    stopping = False

    def _stop(*_args: object) -> None:
        nonlocal stopping
        stopping = True
        worker.request_stop()
        logger.info("worker_stop_requested", worker_id=worker_id)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info(
        "worker_started",
        worker_id=worker_id,
        sandbox_mode=bundle.sandbox_mode,
        adapter_mode=bundle.adapter_mode,
        actor_id=bundle.actor.id,
    )
    try:
        while not stopping and worker.state.value != "stopped":
            try:
                result = worker.run_once(block=True)
            except Exception:
                # Never let one malformed run kill the process.
                logger.exception("worker_run_once_unhandled_error", worker_id=worker_id)
                result = None
            if result is None and not stopping:
                time.sleep(0.05)
    finally:
        worker.shutdown()
        client.close()
        infra.dispose()
        shutdown_tracing()
        logger.info("worker_stopped", worker_id=worker_id)


if __name__ == "__main__":
    run()
