#!/usr/bin/env python3
"""Seed Coding Benchmark v1 and optionally queue a suite execution.

Uses the production infrastructure profile (Postgres/Redis via env).

Examples:

  # Seed only (prints IDs)
  uv run python infrastructure/scripts/seed_and_run_coding_benchmark.py

  # Seed + enqueue all five cases (requires agent/adapter pins)
  uv run python infrastructure/scripts/seed_and_run_coding_benchmark.py \\
    --execute \\
    --agent-id … --agent-version-id … \\
    --adapter-version-id …

Environment:
  DATABASE_URL / REDIS_URL — production infra (same as API/worker)
  Never pass GEMINI_API_KEY on the CLI; the worker reads it from the env.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from agent_eval_api.auth.authorization import AllowAllAuthorization
from agent_eval_api.auth.rbac import ProjectRbacAuthorization
from agent_eval_api.composition import build_membership_store
from agent_eval_application.commands.suite_execution import CreateSuiteRunsCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.platform import (
    CreatePlatform,
    CreatePlatformDraftVersion,
    PublishPlatformVersion,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_application.use_cases.run import CreateRun
from agent_eval_application.use_cases.seed_coding_benchmark import SeedCodingBenchmarkV1
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    GetSuite,
    PublishSuiteVersion,
)
from agent_eval_application.use_cases.suite_execution import CreateSuiteRuns
from agent_eval_infrastructure import RuntimeProfile, build_infrastructure


def _build_seed(infra, auth) -> SeedCodingBenchmarkV1:
    uow = infra.uow_factory
    ids = infra.ids
    events = infra.events
    return SeedCodingBenchmarkV1(
        create_project=CreateProject(uow, ids, auth, events, infra.idempotency),
        create_grader=CreateGrader(uow, ids, auth, events, infra.idempotency),
        create_grader_draft=CreateGraderDraftVersion(uow, ids, auth, events),
        publish_grader=PublishGraderVersion(uow, auth, events),
        create_platform=CreatePlatform(uow, ids, auth, events, infra.idempotency),
        create_platform_draft=CreatePlatformDraftVersion(uow, ids, auth, events),
        publish_platform=PublishPlatformVersion(uow, auth, events),
        create_case=CreateCase(uow, ids, auth, events, infra.idempotency),
        create_prompt_draft=CreatePromptDraftVersion(uow, ids, auth, events),
        create_case_draft=CreateCaseDraftVersion(uow, ids, auth, events),
        publish_case=PublishCaseVersion(uow, auth, events),
        create_suite=CreateSuite(uow, ids, auth, events, infra.idempotency),
        create_suite_draft=CreateSuiteDraftVersion(uow, ids, auth, events),
        publish_suite=PublishSuiteVersion(uow, auth, events),
        get_suite=GetSuite(uow, auth),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actor-id",
        default=os.environ.get("WORKER_ACTOR_ID", "system-worker"),
        help="Actor id used for seeding (must be able to manage projects)",
    )
    parser.add_argument(
        "--allow-all-auth",
        action="store_true",
        help="Bypass RBAC (local/operator only; never use in shared prod)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Also fan out suite runs",
    )
    parser.add_argument("--agent-id")
    parser.add_argument("--agent-version-id")
    parser.add_argument("--adapter-version-id")
    parser.add_argument(
        "--platform-version-id",
        help="Override seeded platform version (defaults to seed output)",
    )
    parser.add_argument(
        "--idempotency-key",
        default=None,
        help="Optional suite-execute Idempotency-Key prefix",
    )
    args = parser.parse_args(argv)

    if args.execute and not all(
        (args.agent_id, args.agent_version_id, args.adapter_version_id)
    ):
        parser.error(
            "--execute requires --agent-id, --agent-version-id, and "
            "--adapter-version-id"
        )

    infra = build_infrastructure(profile=RuntimeProfile.PRODUCTION)
    try:
        if args.allow_all_auth:
            auth = AllowAllAuthorization()
        else:
            memberships = build_membership_store(infra)
            auth = ProjectRbacAuthorization(memberships)
        actor = Actor(id=args.actor_id)
        seeded = _build_seed(infra, auth).execute(actor=actor)
        payload: dict[str, object] = {
            "project_id": seeded.project_id,
            "suite_id": seeded.suite_id,
            "suite_version_id": seeded.suite_version_id,
            "platform_version_id": seeded.platform_version_id,
            "grader_id": seeded.grader_id,
            "grader_version_id": seeded.grader_version_id,
            "case_version_ids": list(seeded.case_version_ids),
            "catalog_key": seeded.suite.catalog_key,
        }
        if args.execute:
            create_run = CreateRun(
                infra.uow_factory,
                infra.ids,
                auth,
                infra.events,
                infra.run_queue,
                infra.idempotency,
            )
            execution = CreateSuiteRuns(infra.uow_factory, auth, create_run).execute(
                CreateSuiteRunsCommand(
                    actor=actor,
                    suite_id=seeded.suite_id,
                    suite_version_id=seeded.suite_version_id,
                    agent_id=args.agent_id,
                    agent_version_id=args.agent_version_id,
                    adapter_version_id=args.adapter_version_id,
                    platform_version_id=(
                        args.platform_version_id or seeded.platform_version_id
                    ),
                    idempotency_key=args.idempotency_key,
                )
            )
            payload["execution_group_id"] = execution.execution_group_id
            payload["total_cases"] = execution.total_cases
            payload["run_ids"] = [entry.run.id for entry in execution.runs]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    finally:
        infra.dispose()


if __name__ == "__main__":
    sys.exit(main())
