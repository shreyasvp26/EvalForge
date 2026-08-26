"""Composition root — wire Application use cases over Infrastructure adapters.

Dependency direction (Backend Architecture §5):

    API routers → Application use cases (interfaces / execute)
    Composition root → Infrastructure (concrete adapters) + Configuration

Routers never import Infrastructure or Domain entities.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.github_publication import GitHubConnectionPort
from agent_eval_application.ports.identity import IdentityPort
from agent_eval_application.ports.oauth_identity import OAuthIdentityPort
from agent_eval_application.ports.provider_connections import ProviderConnectionPort
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    GetAdapter,
    GetAgent,
    ListAdapters,
    ListAgents,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.auth import GetCurrentUser, Login
from agent_eval_application.use_cases.benchmark_matrix import BuildBenchmarkMatrix
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    DeprecateCase,
    GetCase,
    ListCasesByProject,
    PublishCaseVersion,
    PublishPromptVersion,
)
from agent_eval_application.use_cases.github_publication import (
    CreateGitHubConnection,
    ListGitHubConnections,
    RevokeGitHubConnection,
)
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    GetGrader,
    ListGraders,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.platform import (
    CreatePlatform,
    CreatePlatformDraftVersion,
    GetPlatform,
    ListPlatforms,
    PublishPlatformVersion,
)
from agent_eval_application.use_cases.project import (
    CreateProject,
    DeprecateProject,
    GetProject,
    ListProjects,
    RenameProject,
    UpdateProjectSettings,
)
from agent_eval_application.use_cases.provenance import GetRunProvenance
from agent_eval_application.use_cases.provider_connections import (
    CreateProviderConnection,
    ListConnectionModels,
    ListProviderConnections,
    ListProviders,
    RevokeProviderConnection,
    VerifyProviderConnection,
)
from agent_eval_application.use_cases.publish_run import PublishEvaluationRun
from agent_eval_application.use_cases.run import (
    CancelRun,
    CreateRun,
    GetRun,
    GetRunArtifacts,
    GetRunEvents,
    GetRunScores,
    ListRunsByProject,
)
from agent_eval_application.use_cases.run_comparison import CompareRuns
from agent_eval_application.use_cases.run_diagnosis import DiagnoseRunFailure
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    DeprecateSuite,
    GetSuite,
    ListBenchmarkCatalog,
    ListSuitesByProject,
    PublishSuiteVersion,
    RetireSuiteVersion,
    UpdateSuiteCatalog,
)
from agent_eval_application.use_cases.suite_execution import (
    AggregateSuiteResults,
    CreateSuiteRuns,
)
from agent_eval_infrastructure import (
    InfrastructureContainer,
    RuntimeProfile,
    build_infrastructure,
)
from agent_eval_infrastructure.auth import (
    InMemoryIdentityStore,
    InMemoryMembershipStore,
    InMemoryOAuthIdentityStore,
    InMemoryProviderConnectionStore,
    MembershipStore,
    SqlAlchemyIdentityStore,
    SqlAlchemyMembershipStore,
    SqlAlchemyOAuthIdentityStore,
    SqlAlchemyProviderConnectionStore,
    ensure_bootstrap_user,
)
from agent_eval_infrastructure.auth.github_connection import (
    InMemoryGitHubConnectionStore,
    SqlAlchemyGitHubConnectionStore,
)
from agent_eval_infrastructure.github.publisher import HttpGitHubPullRequestPublisher
from agent_eval_infrastructure.providers import HttpProviderVerifier

from agent_eval_api.auth.oauth.providers.github import GitHubOAuthProvider
from agent_eval_api.auth.oauth.providers.google import GoogleOAuthProvider
from agent_eval_api.auth.oauth.service import OAuthService
from agent_eval_api.auth.oauth.stores import (
    InMemoryOAuthExchangeStore,
    InMemoryOAuthStateStore,
    OAuthExchangeStore,
    OAuthStateStore,
    RedisOAuthExchangeStore,
    RedisOAuthStateStore,
)
from agent_eval_api.auth.rbac import ProjectRbacAuthorization
from agent_eval_api.config import ApiSettings, load_api_settings


@dataclass(slots=True)
class ApplicationServices:
    """API-facing Application use cases (public Control Plane surface)."""

    # Auth
    login: Login
    get_current_user: GetCurrentUser

    # Projects
    create_project: CreateProject
    get_project: GetProject
    list_projects: ListProjects
    rename_project: RenameProject
    update_project_settings: UpdateProjectSettings
    deprecate_project: DeprecateProject

    # Suites
    create_suite: CreateSuite
    get_suite: GetSuite
    list_suites_by_project: ListSuitesByProject
    list_benchmark_catalog: ListBenchmarkCatalog
    update_suite_catalog: UpdateSuiteCatalog
    create_suite_draft_version: CreateSuiteDraftVersion
    publish_suite_version: PublishSuiteVersion
    retire_suite_version: RetireSuiteVersion
    deprecate_suite: DeprecateSuite
    create_suite_runs: CreateSuiteRuns
    aggregate_suite_results: AggregateSuiteResults

    # Cases + Prompts
    create_case: CreateCase
    get_case: GetCase
    list_cases_by_project: ListCasesByProject
    create_case_draft_version: CreateCaseDraftVersion
    publish_case_version: PublishCaseVersion
    deprecate_case: DeprecateCase
    create_prompt_draft_version: CreatePromptDraftVersion
    publish_prompt_version: PublishPromptVersion

    # Agents + Adapters
    create_agent: CreateAgent
    get_agent: GetAgent
    list_agents: ListAgents
    create_agent_draft_version: CreateAgentDraftVersion
    publish_agent_version: PublishAgentVersion
    create_adapter: CreateAdapter
    get_adapter: GetAdapter
    list_adapters: ListAdapters
    create_adapter_draft_version: CreateAdapterDraftVersion
    publish_adapter_version: PublishAdapterVersion

    # Graders
    create_grader: CreateGrader
    get_grader: GetGrader
    list_graders: ListGraders
    create_grader_draft_version: CreateGraderDraftVersion
    publish_grader_version: PublishGraderVersion

    # Platforms
    create_platform: CreatePlatform
    get_platform: GetPlatform
    list_platforms: ListPlatforms
    create_platform_draft_version: CreatePlatformDraftVersion
    publish_platform_version: PublishPlatformVersion

    # Runs (public surface only — worker lifecycle stays off REST)
    create_run: CreateRun
    get_run: GetRun
    list_runs_by_project: ListRunsByProject
    get_run_events: GetRunEvents
    get_run_artifacts: GetRunArtifacts
    get_run_scores: GetRunScores
    get_run_provenance: GetRunProvenance
    compare_runs: CompareRuns
    build_benchmark_matrix: BuildBenchmarkMatrix
    diagnose_run_failure: DiagnoseRunFailure
    cancel_run: CancelRun

    # Phase 13 — provider catalog + BYOK connections
    list_providers: ListProviders
    create_provider_connection: CreateProviderConnection
    list_provider_connections: ListProviderConnections
    revoke_provider_connection: RevokeProviderConnection
    verify_provider_connection: VerifyProviderConnection
    list_connection_models: ListConnectionModels

    # Phase 14 — GitHub publication
    create_github_connection: CreateGitHubConnection
    list_github_connections: ListGitHubConnections
    revoke_github_connection: RevokeGitHubConnection
    publish_evaluation_run: PublishEvaluationRun


@dataclass(slots=True)
class ApiContainer:
    """Process-scoped Control Plane composition root."""

    settings: ApiSettings
    infrastructure: InfrastructureContainer
    auth: AuthorizationPort
    services: ApplicationServices
    memberships: MembershipStore
    identity: IdentityPort
    oauth_identities: OAuthIdentityPort
    oauth: OAuthService
    provider_connections: ProviderConnectionPort
    github_connections: GitHubConnectionPort

    def dispose(self) -> None:
        self.infrastructure.dispose()

    def readiness_checks(self) -> dict[str, str]:
        """Probe Infrastructure for readiness without exposing tech to routers."""
        from sqlalchemy import text

        checks: dict[str, str] = {"composition": "ok"}
        try:
            with self.infrastructure.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:  # noqa: BLE001 — readiness must never raise
            checks["database"] = "unavailable"
        return checks


def build_oauth_identity_store(
    infrastructure: InfrastructureContainer,
) -> OAuthIdentityPort:
    if infrastructure.profile is RuntimeProfile.MEMORY:
        return InMemoryOAuthIdentityStore()
    return SqlAlchemyOAuthIdentityStore(infrastructure.session_factory)


def build_oauth_stores(
    infrastructure: InfrastructureContainer,
) -> tuple[OAuthStateStore, OAuthExchangeStore]:
    if infrastructure.profile is RuntimeProfile.MEMORY or infrastructure.redis is None:
        return InMemoryOAuthStateStore(), InMemoryOAuthExchangeStore()
    return (
        RedisOAuthStateStore(infrastructure.redis),
        RedisOAuthExchangeStore(infrastructure.redis),
    )


def build_oauth_service(
    *,
    settings: ApiSettings,
    infrastructure: InfrastructureContainer,
    identity: IdentityPort,
    oauth_identities: OAuthIdentityPort,
) -> OAuthService:
    state_store, exchange_store = build_oauth_stores(infrastructure)
    google = None
    if settings.google_oauth_configured():
        google = GoogleOAuthProvider(
            client_id=settings.google_client_id or "",
            client_secret=settings.google_client_secret or "",
            redirect_uri=settings.google_redirect_uri or "",
        )
    github = None
    if settings.github_oauth_configured():
        github = GitHubOAuthProvider(
            client_id=settings.github_client_id or "",
            client_secret=settings.github_client_secret or "",
            redirect_uri=settings.github_redirect_uri or "",
        )
    return OAuthService(
        identity=identity,
        oauth_identities=oauth_identities,
        state_store=state_store,
        exchange_store=exchange_store,
        web_app_url=settings.web_app_url,
        google=google,
        github=github,
    )


def build_membership_store(
    infrastructure: InfrastructureContainer,
) -> MembershipStore:
    if infrastructure.profile is RuntimeProfile.MEMORY:
        return InMemoryMembershipStore()
    return SqlAlchemyMembershipStore(infrastructure.session_factory)


def build_identity_store(
    infrastructure: InfrastructureContainer,
) -> IdentityPort:
    if infrastructure.profile is RuntimeProfile.MEMORY:
        return InMemoryIdentityStore()
    return SqlAlchemyIdentityStore(infrastructure.session_factory)


def build_github_connection_store(
    infrastructure: InfrastructureContainer,
) -> GitHubConnectionPort:
    if infrastructure.profile is RuntimeProfile.MEMORY:
        return InMemoryGitHubConnectionStore()
    return SqlAlchemyGitHubConnectionStore(infrastructure.session_factory)


def build_provider_connection_store(
    infrastructure: InfrastructureContainer,
) -> ProviderConnectionPort:
    if infrastructure.profile is RuntimeProfile.MEMORY:
        return InMemoryProviderConnectionStore()
    return SqlAlchemyProviderConnectionStore(infrastructure.session_factory)


def build_application_services(
    infrastructure: InfrastructureContainer,
    auth: AuthorizationPort,
    identity: IdentityPort,
    provider_connections: ProviderConnectionPort | None = None,
    github_connections: GitHubConnectionPort | None = None,
) -> ApplicationServices:
    """Construct Application use cases from Infrastructure ports."""
    uow = infrastructure.uow_factory
    ids = infrastructure.ids
    events = infrastructure.events
    idempotency = infrastructure.idempotency
    run_queue = infrastructure.run_queue
    connections = provider_connections or build_provider_connection_store(
        infrastructure
    )
    github = github_connections or build_github_connection_store(infrastructure)
    github_publisher = HttpGitHubPullRequestPublisher()
    provider_verifier = HttpProviderVerifier()
    create_run = CreateRun(
        uow,
        ids,
        auth,
        events,
        run_queue,
        idempotency,
        provider_connections=connections,
    )
    get_run = GetRun(uow, auth)

    return ApplicationServices(
        login=Login(identity),
        get_current_user=GetCurrentUser(identity),
        create_project=CreateProject(uow, ids, auth, events, idempotency),
        get_project=GetProject(uow, auth),
        list_projects=ListProjects(uow, auth),
        rename_project=RenameProject(uow, auth, events),
        update_project_settings=UpdateProjectSettings(uow, auth, events),
        deprecate_project=DeprecateProject(uow, auth, events),
        create_suite=CreateSuite(uow, ids, auth, events, idempotency),
        get_suite=GetSuite(uow, auth),
        list_suites_by_project=ListSuitesByProject(uow, auth),
        list_benchmark_catalog=ListBenchmarkCatalog(uow, auth),
        update_suite_catalog=UpdateSuiteCatalog(uow, auth, events),
        create_suite_draft_version=CreateSuiteDraftVersion(uow, ids, auth, events),
        publish_suite_version=PublishSuiteVersion(uow, auth, events),
        retire_suite_version=RetireSuiteVersion(uow, auth, events),
        deprecate_suite=DeprecateSuite(uow, auth, events),
        create_suite_runs=CreateSuiteRuns(uow, auth, create_run),
        aggregate_suite_results=AggregateSuiteResults(uow, auth),
        create_case=CreateCase(uow, ids, auth, events, idempotency),
        get_case=GetCase(uow, auth),
        list_cases_by_project=ListCasesByProject(uow, auth),
        create_case_draft_version=CreateCaseDraftVersion(uow, ids, auth, events),
        publish_case_version=PublishCaseVersion(uow, auth, events),
        deprecate_case=DeprecateCase(uow, auth, events),
        create_prompt_draft_version=CreatePromptDraftVersion(uow, ids, auth, events),
        publish_prompt_version=PublishPromptVersion(uow, auth, events),
        create_agent=CreateAgent(uow, ids, auth, events, idempotency),
        get_agent=GetAgent(uow, auth),
        list_agents=ListAgents(uow, auth),
        create_agent_draft_version=CreateAgentDraftVersion(uow, ids, auth, events),
        publish_agent_version=PublishAgentVersion(uow, auth, events),
        create_adapter=CreateAdapter(uow, ids, auth, events, idempotency),
        get_adapter=GetAdapter(uow, auth),
        list_adapters=ListAdapters(uow, auth),
        create_adapter_draft_version=CreateAdapterDraftVersion(uow, ids, auth, events),
        publish_adapter_version=PublishAdapterVersion(uow, auth, events),
        create_grader=CreateGrader(uow, ids, auth, events, idempotency),
        get_grader=GetGrader(uow, auth),
        list_graders=ListGraders(uow, auth),
        create_grader_draft_version=CreateGraderDraftVersion(uow, ids, auth, events),
        publish_grader_version=PublishGraderVersion(uow, auth, events),
        create_platform=CreatePlatform(uow, ids, auth, events, idempotency),
        get_platform=GetPlatform(uow, auth),
        list_platforms=ListPlatforms(uow, auth),
        create_platform_draft_version=CreatePlatformDraftVersion(
            uow, ids, auth, events
        ),
        publish_platform_version=PublishPlatformVersion(uow, auth, events),
        create_run=create_run,
        get_run=get_run,
        list_runs_by_project=ListRunsByProject(uow, auth),
        get_run_events=GetRunEvents(uow, auth),
        get_run_artifacts=GetRunArtifacts(uow, auth),
        get_run_scores=GetRunScores(uow, auth),
        get_run_provenance=GetRunProvenance(uow, auth),
        compare_runs=CompareRuns(uow, auth),
        build_benchmark_matrix=BuildBenchmarkMatrix(uow, auth),
        diagnose_run_failure=DiagnoseRunFailure(uow, auth),
        cancel_run=CancelRun(uow, auth, events),
        list_providers=ListProviders(connections),
        create_provider_connection=CreateProviderConnection(connections),
        list_provider_connections=ListProviderConnections(connections),
        revoke_provider_connection=RevokeProviderConnection(connections),
        verify_provider_connection=VerifyProviderConnection(
            connections, provider_verifier
        ),
        list_connection_models=ListConnectionModels(connections, provider_verifier),
        create_github_connection=CreateGitHubConnection(github),
        list_github_connections=ListGitHubConnections(github),
        revoke_github_connection=RevokeGitHubConnection(github),
        publish_evaluation_run=PublishEvaluationRun(
            uow,
            events,
            github,
            github_publisher,
            get_run=get_run,
        ),
    )


def build_api_container(
    *,
    settings: ApiSettings | None = None,
    infrastructure: InfrastructureContainer | None = None,
    auth: AuthorizationPort | None = None,
    memberships: MembershipStore | None = None,
    identity: IdentityPort | None = None,
    oauth_identities: OAuthIdentityPort | None = None,
    oauth: OAuthService | None = None,
    provider_connections: ProviderConnectionPort | None = None,
    github_connections: GitHubConnectionPort | None = None,
    profile: RuntimeProfile | None = None,
) -> ApiContainer:
    """Assemble the Control Plane composition root."""
    api_settings = settings or load_api_settings()
    infra = infrastructure or build_infrastructure(profile=profile)
    store = memberships or build_membership_store(infra)
    identity_store = identity or build_identity_store(infra)
    oauth_store = oauth_identities or build_oauth_identity_store(infra)
    connection_store = provider_connections or build_provider_connection_store(infra)
    github_store = github_connections or build_github_connection_store(infra)
    if api_settings.auth_bootstrap_email and api_settings.auth_bootstrap_password:
        ensure_bootstrap_user(
            identity_store,
            email=api_settings.auth_bootstrap_email,
            password=api_settings.auth_bootstrap_password,
            display_name=api_settings.auth_bootstrap_display_name,
        )
    authorization = auth or ProjectRbacAuthorization(store)
    services = build_application_services(
        infra,
        authorization,
        identity_store,
        provider_connections=connection_store,
        github_connections=github_store,
    )
    oauth_service = oauth or build_oauth_service(
        settings=api_settings,
        infrastructure=infra,
        identity=identity_store,
        oauth_identities=oauth_store,
    )
    return ApiContainer(
        settings=api_settings,
        infrastructure=infra,
        auth=authorization,
        services=services,
        memberships=store,
        identity=identity_store,
        oauth_identities=oauth_store,
        oauth=oauth_service,
        provider_connections=connection_store,
        github_connections=github_store,
    )
