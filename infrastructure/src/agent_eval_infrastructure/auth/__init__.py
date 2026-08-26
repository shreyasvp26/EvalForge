"""Infrastructure auth persistence package."""

from agent_eval_infrastructure.auth.identity import (
    InMemoryIdentityStore,
    SqlAlchemyIdentityStore,
    UserOrm,
    ensure_bootstrap_user,
    hash_password,
    verify_password,
)
from agent_eval_infrastructure.auth.membership import (
    ROLE_RANK,
    InMemoryMembershipStore,
    MembershipStore,
    ProjectMembershipOrm,
    ProjectRole,
    SqlAlchemyMembershipStore,
)
from agent_eval_infrastructure.auth.oauth_identity import (
    InMemoryOAuthIdentityStore,
    OAuthIdentityOrm,
    SqlAlchemyOAuthIdentityStore,
)
from agent_eval_infrastructure.auth.provider_connection import (
    InMemoryProviderConnectionStore,
    ProviderConnectionOrm,
    SqlAlchemyProviderConnectionStore,
)

__all__ = [
    "ROLE_RANK",
    "InMemoryIdentityStore",
    "InMemoryOAuthIdentityStore",
    "InMemoryMembershipStore",
    "InMemoryProviderConnectionStore",
    "OAuthIdentityOrm",
    "MembershipStore",
    "ProjectMembershipOrm",
    "ProjectRole",
    "ProviderConnectionOrm",
    "SqlAlchemyIdentityStore",
    "SqlAlchemyOAuthIdentityStore",
    "SqlAlchemyMembershipStore",
    "SqlAlchemyProviderConnectionStore",
    "UserOrm",
    "ensure_bootstrap_user",
    "hash_password",
    "verify_password",
]
