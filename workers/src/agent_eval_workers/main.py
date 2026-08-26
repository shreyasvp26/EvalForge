"""Background Worker process entry — claim loop over Redis.

Composition root for the Execution Plane process. Wires Infrastructure +
production LifecycleOrchestrator (Sandbox / Adapter / Graders / Application)
into ``WorkerRuntime`` without importing the API Layer.
"""

from __future__ import annotations

import os
import signal
import threading
import time
from typing import cast

from agent_eval_infrastructure import RuntimeProfile, build_infrastructure
from agent_eval_infrastructure.auth.github_connection import (
    SqlAlchemyGitHubConnectionStore,
)
from agent_eval_infrastructure.auth.provider_connection import (
    SqlAlchemyProviderConnectionStore,
)
from agent_eval_infrastructure.github.publisher import HttpGitHubPullRequestPublisher
from agent_eval_infrastructure.queue.redis_cancellation import RedisRunCancellationStore
from agent_eval_infrastructure.queue.redis_run_events import RedisRunEventFanout
from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue
from agent_eval_shared.config import Environment, LogLevel
from agent_eval_shared.log import configure_logging, get_logger
from agent_eval_shared.metrics import configure_metrics
from agent_eval_shared.tracing import configure_tracing, shutdown_tracing
from redis import Redis

from agent_eval_workers.cancellation.redis_registry import RedisCancellationRegistry
from agent_eval_workers.concurrency import resolve_worker_concurrency
from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.queue_redis import RedisWorkerQueue

logger = get_logger("agent_eval_workers.main")


def _claim_loop(*, worker, worker_id: str, stopping: threading.Event) -> None:
    while not stopping.is_set() and worker.state.value != "stopped":
        try:
            result = worker.run_once(block=True)
        except Exception:
            logger.exception("worker_run_once_unhandled_error", worker_id=worker_id)
            result = None
        if result is None and not stopping.is_set():
            time.sleep(0.05)


def run() -> None:
    """CLI entry: ``evalforge-worker``."""
    environment = cast(Environment, os.environ.get("ENVIRONMENT", "production"))
    log_level = cast(LogLevel, os.environ.get("LOG_LEVEL", "info"))
    worker_id = os.environ.get("WORKER_ID", "worker-1")
    concurrency = resolve_worker_concurrency()

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
    claim_timeout = float(
        os.environ.get(
            "RUN_QUEUE_CLAIM_TIMEOUT_SECONDS",
            str(infra.settings.run_queue_claim_timeout_seconds),
        )
    )
    # socket_timeout must exceed BLMOVE block time or idle waits raise TimeoutError.
    client = Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=None,
        socket_connect_timeout=5.0,
    )
    run_queue = RedisRunQueue(
        client,
        key_prefix=os.environ.get(
            "RUN_QUEUE_KEY_PREFIX", infra.settings.run_queue_key_prefix
        ),
        claim_timeout_seconds=claim_timeout,
    )
    worker_queue = RedisWorkerQueue(run_queue)

    cancel_store = RedisRunCancellationStore(
        client,
        key_prefix=os.environ.get("RUN_CANCEL_KEY_PREFIX", "evalforge:cancel"),
    )
    cancellation = RedisCancellationRegistry(cancel_store)
    event_fanout = RedisRunEventFanout(
        client,
        channel_prefix=os.environ.get(
            "RUN_EVENTS_CHANNEL_PREFIX", "evalforge:run-events"
        ),
    )

    timeout_raw = os.environ.get("WORKER_EXECUTION_TIMEOUT_SECONDS")
    execution_timeout = float(timeout_raw) if timeout_raw else None

    stopping = threading.Event()
    bundles = []
    threads: list[threading.Thread] = []

    def _stop(*_args: object) -> None:
        stopping.set()
        for bundle in bundles:
            bundle.worker.request_stop()
        logger.info("worker_stop_requested", worker_id=worker_id)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    try:
        for index in range(concurrency):
            slot_id = worker_id if concurrency == 1 else f"{worker_id}-{index + 1}"
            bundle = build_production_worker(
                queue=worker_queue,
                uow_factory=infra.uow_factory,
                ids=infra.ids,
                events=infra.events,
                worker_id=slot_id,
                execution_timeout_seconds=execution_timeout,
                cancellation=cancellation,
                object_storage=infra.object_storage,
                event_fanout=event_fanout,
                provider_connections=SqlAlchemyProviderConnectionStore(
                    infra.session_factory
                ),
                github_connections=SqlAlchemyGitHubConnectionStore(
                    infra.session_factory
                ),
                github_publisher=HttpGitHubPullRequestPublisher(),
            )
            bundles.append(bundle)
            if concurrency == 1:
                logger.info(
                    "worker_started",
                    worker_id=slot_id,
                    sandbox_mode=bundle.sandbox_mode,
                    adapter_mode=bundle.adapter_mode,
                    actor_id=bundle.actor.id,
                    concurrency=concurrency,
                )
                _claim_loop(worker=bundle.worker, worker_id=slot_id, stopping=stopping)
            else:
                thread = threading.Thread(
                    target=_claim_loop,
                    kwargs={
                        "worker": bundle.worker,
                        "worker_id": slot_id,
                        "stopping": stopping,
                    },
                    name=f"evalforge-worker-{slot_id}",
                    daemon=True,
                )
                threads.append(thread)

        if concurrency > 1:
            logger.info(
                "worker_pool_started",
                worker_id=worker_id,
                concurrency=concurrency,
                sandbox_mode=bundles[0].sandbox_mode,
                adapter_mode=bundles[0].adapter_mode,
                actor_id=bundles[0].actor.id,
            )
            for thread in threads:
                thread.start()
            while not stopping.is_set():
                time.sleep(0.25)
            for thread in threads:
                thread.join(timeout=30.0)
    finally:
        for bundle in bundles:
            bundle.worker.shutdown()
        client.close()
        infra.dispose()
        shutdown_tracing()
        logger.info("worker_stopped", worker_id=worker_id)


if __name__ == "__main__":
    run()
