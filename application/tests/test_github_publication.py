"""Application tests for GitHub publication use case."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.ports.github_publication import WorkspaceFileChange
from agent_eval_application.publication.eligibility import (
    evaluate_publication_eligibility,
)
from agent_eval_application.use_cases.github_publication import (
    CreateEvaluationPullRequest,
    CreateEvaluationPullRequestCommand,
    CreateGitHubConnection,
    CreateGitHubConnectionCommand,
    parse_github_repository,
)
from agent_eval_domain.execution.publication import PublicationStatus, RunPublication
from agent_eval_infrastructure.auth.github_connection import (
    InMemoryGitHubConnectionStore,
)
from agent_eval_infrastructure.github.publisher import FakeGitHubPullRequestPublisher
from agent_eval_infrastructure.secrets.fernet_box import load_provider_secret_key


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_CREDENTIALS_KEY", "x" * 32)
    monkeypatch.setenv("JWT_SECRET_KEY", "y" * 32)


def test_parse_github_repository_https_and_ssh() -> None:
    assert parse_github_repository("https://github.com/acme/demo.git") == (
        "acme",
        "demo",
    )
    assert parse_github_repository("git@github.com:acme/demo.git") == ("acme", "demo")


def test_github_connection_never_returns_plaintext() -> None:
    store = InMemoryGitHubConnectionStore(secret_key=load_provider_secret_key())
    create = CreateGitHubConnection(store)
    conn = create.execute(
        CreateGitHubConnectionCommand(
            actor=Actor(id="user-1"),
            token="ghp_testtoken_not_for_production",
            display_name="Work",
        )
    )
    public = conn.to_public_dict()
    assert "ghp_" not in str(public)
    assert public["masked_token"].startswith("••••")
    _c, secret = store.resolve_token_for_user(user_id="user-1", connection_id=conn.id)
    assert secret.startswith("ghp_")


class _FakeUow:
    def __init__(self, run: object) -> None:
        self.run = run
        self.runs = SimpleNamespace(get=lambda _id: run, save=lambda _r: None)

    def __enter__(self) -> _FakeUow:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        return None


class _FakeRun:
    def __init__(self) -> None:
        self.id = SimpleNamespace(value="run-1")
        self.status = SimpleNamespace(value="completed")
        self.publication = RunPublication()
        self.scores = [
            SimpleNamespace(
                id=SimpleNamespace(value="s1"),
                grader_id=SimpleNamespace(value="g1"),
                grader_version_id=SimpleNamespace(value="gv1"),
                value=SimpleNamespace(
                    passed=True,
                    numeric=1.0,
                    categorical=None,
                    detail={"family": "objective"},
                ),
                explanation_artifact_id=None,
            )
        ]
        self.pins = SimpleNamespace(
            project_id=SimpleNamespace(value="p1"),
            case_version_id=SimpleNamespace(value="cv1"),
            prompt_version_id=SimpleNamespace(value="pv1"),
            agent_version_id=SimpleNamespace(value="av1"),
            adapter_version_id=SimpleNamespace(value="adv1"),
            platform_version_id=SimpleNamespace(value="pl1"),
            grader_version_ids=(SimpleNamespace(value="gv1"),),
            suite_version_id=None,
        )
        self.failure_reason = None
        self.failure_category = None
        self.cancellation_reason = None
        self.sandbox = None
        self.expected_grader_count = 1
        self.is_partially_graded = False
        self.created_at = __import__("datetime").datetime.now(
            __import__("datetime").UTC
        )
        self.cost = None
        self.execution_mode = None
        self.execution_metadata = {}
        self.runtime_request = {}
        self.execution_group_id = None
        self._events: list[object] = []

    def record_publication(self, publication: RunPublication) -> None:
        self.publication = publication

    def pull_events(self) -> list[object]:
        return []


def test_create_evaluation_pull_request_publishes_on_pass() -> None:
    from agent_eval_application.dto.run import RunDTO

    store = InMemoryGitHubConnectionStore(secret_key=load_provider_secret_key())
    CreateGitHubConnection(store).execute(
        CreateGitHubConnectionCommand(
            actor=Actor(id="user-1"),
            token="ghp_testtoken_not_for_production",
        )
    )
    publisher = FakeGitHubPullRequestPublisher()
    run = _FakeRun()

    def get_run_execute(query: object) -> RunDTO:
        del query
        return RunDTO.from_domain(run)  # type: ignore[arg-type]

    # RunDTO.from_domain expects EvaluationRun — build DTO manually instead.
    dto = RunDTO(
        id="run-1",
        status="completed",
        created_at=run.created_at,
        pins=SimpleNamespace(  # type: ignore[arg-type]
            project_id="p1",
            case_version_id="cv1",
            prompt_version_id="pv1",
            agent_version_id="av1",
            adapter_version_id="adv1",
            platform_version_id="pl1",
            grader_version_ids=("gv1",),
            suite_version_id=None,
        ),
        failure_reason=None,
        failure_category=None,
        cancellation_reason=None,
        sandbox_id=None,
        expected_grader_count=1,
        produced_score_count=1,
        is_partially_graded=False,
        scores=(
            SimpleNamespace(  # type: ignore[arg-type]
                id="s1",
                grader_id="g1",
                grader_version_id="gv1",
                value=SimpleNamespace(
                    numeric=1.0,
                    categorical=None,
                    passed=True,
                    detail={"family": "objective"},
                ),
                explanation_artifact_id=None,
            ),
        ),
        telemetry=SimpleNamespace(  # type: ignore[arg-type]
            wall_clock_ms=None,
            compute_ms=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            provider_usage_available=False,
        ),
        publication={},
    )

    class GetRun:
        def execute(self, query: object) -> RunDTO:
            del query
            # Refresh publication from mutable run between calls.
            return RunDTO(
                id=dto.id,
                status=dto.status,
                created_at=dto.created_at,
                pins=dto.pins,
                failure_reason=None,
                failure_category=None,
                cancellation_reason=None,
                sandbox_id=None,
                expected_grader_count=1,
                produced_score_count=1,
                is_partially_graded=False,
                scores=dto.scores,
                telemetry=dto.telemetry,
                publication=dict(run.publication.to_public_dict()),
            )

    use_case = CreateEvaluationPullRequest(
        uow_factory=lambda: _FakeUow(run),
        events=SimpleNamespace(dispatch=lambda _e: None),
        github_connections=store,
        publisher=publisher,
        get_run=GetRun(),
    )
    result = use_case.execute(
        CreateEvaluationPullRequestCommand(
            actor=Actor(id="user-1"),
            run_id="run-1",
            changes=(
                WorkspaceFileChange(
                    path="hello.py", content=b"print('hi')\n", status="added"
                ),
            ),
            repository_url="https://github.com/acme/demo",
            base_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
            case_id="case-1",
            task_title="Add hello",
            agent_label="gemini",
            model_label="gemini-2.0-flash",
            provider_label="google",
            score_summary="passed",
        )
    )
    assert result.publication["status"] == PublicationStatus.PUBLISHED.value
    assert result.publication["pull_request_url"]
    assert run.publication.status is PublicationStatus.PUBLISHED
    # Evaluation status unchanged
    assert dto.status == "completed"

    # Idempotent retry
    result2 = use_case.execute(
        CreateEvaluationPullRequestCommand(
            actor=Actor(id="user-1"),
            run_id="run-1",
            changes=(
                WorkspaceFileChange(
                    path="hello.py", content=b"print('hi')\n", status="added"
                ),
            ),
            repository_url="https://github.com/acme/demo",
            base_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
            case_id="case-1",
            task_title="Add hello",
        )
    )
    assert result2.publication["status"] == PublicationStatus.PUBLISHED.value
    assert len(publisher.publish_calls) == 1


def test_publication_failure_does_not_change_evaluation() -> None:
    store = InMemoryGitHubConnectionStore(secret_key=load_provider_secret_key())
    CreateGitHubConnection(store).execute(
        CreateGitHubConnectionCommand(
            actor=Actor(id="user-1"),
            token="ghp_testtoken_not_for_production",
        )
    )
    publisher = FakeGitHubPullRequestPublisher()
    publisher.fail_next = "push rejected by policy"
    run = _FakeRun()

    class GetRun:
        def execute(self, query: object) -> object:
            del query
            return SimpleNamespace(
                id="run-1",
                status="completed",
                scores=[
                    SimpleNamespace(
                        value=SimpleNamespace(
                            passed=True, numeric=1.0, detail={"family": "objective"}
                        )
                    )
                ],
                publication=dict(run.publication.to_public_dict()),
            )

    use_case = CreateEvaluationPullRequest(
        uow_factory=lambda: _FakeUow(run),
        events=SimpleNamespace(dispatch=lambda _e: None),
        github_connections=store,
        publisher=publisher,
        get_run=GetRun(),  # type: ignore[arg-type]
    )
    result = use_case.execute(
        CreateEvaluationPullRequestCommand(
            actor=Actor(id="user-1"),
            run_id="run-1",
            changes=(WorkspaceFileChange(path="a.py", content=b"a", status="added"),),
            repository_url="https://github.com/acme/demo",
            base_commit_sha="abc1234",
            case_id="case-1",
            task_title="Task",
        )
    )
    assert result.publication["status"] == PublicationStatus.FAILED.value
    assert run.publication.status is PublicationStatus.FAILED
    # Fake run still "completed" — evaluation untouched
    assert run.status.value == "completed"


def test_fail_scores_skip_publication() -> None:
    result = evaluate_publication_eligibility(
        run_status="completed",
        scores=[
            SimpleNamespace(
                value=SimpleNamespace(
                    passed=False, numeric=0.0, detail={"family": "objective"}
                )
            )
        ],
        workspace_available=True,
        github_authorized=True,
        repository_url="https://github.com/acme/demo",
        base_commit_sha="abc",
    )
    assert result.eligible is False
    assert "objective" in result.reason or result.evaluation_passed is False
