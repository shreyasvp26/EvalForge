"""GitHub OAuth provider."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from agent_eval_application.ports.oauth_identity import OAuthProviderIdentity

from agent_eval_api.auth.oauth.providers.base import OAuthAuthorizationRequest


@dataclass(slots=True)
class GitHubOAuthProvider:
    client_id: str
    client_secret: str
    redirect_uri: str
    provider: str = "github"

    def build_authorization_url(
        self, *, state: str, nonce: str
    ) -> OAuthAuthorizationRequest:
        del nonce  # GitHub OAuth does not use OIDC nonce.
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "true",
        }
        return OAuthAuthorizationRequest(
            authorization_url=f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        )

    async def exchange_code(self, *, code: str, nonce: str) -> OAuthProviderIdentity:
        del nonce
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            access_token = token_payload.get("access_token")
            if not access_token:
                raise ValueError("GitHub token response missing access_token")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            user_response = await client.get(
                "https://api.github.com/user",
                headers=headers,
            )
            user_response.raise_for_status()
            profile = user_response.json()

            subject = str(profile.get("id") or "").strip()
            if not subject:
                raise ValueError("GitHub profile missing user id")

            display_name = str(
                profile.get("name") or profile.get("login") or subject
            ).strip()
            email = str(profile.get("email") or "").strip()
            email_verified = bool(email)

            if not email:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers,
                )
                emails_response.raise_for_status()
                emails = emails_response.json()
                email, email_verified = _select_verified_github_email(emails)

        if not email:
            raise ValueError("GitHub account has no accessible email")
        if not email_verified:
            raise ValueError("GitHub account email is not verified")

        return OAuthProviderIdentity(
            provider="github",
            provider_user_id=subject,
            email=email,
            email_verified=True,
            display_name=display_name,
        )


def _select_verified_github_email(emails: list[object]) -> tuple[str, bool]:
    primary_verified = ""
    first_verified = ""
    for entry in emails:
        if not isinstance(entry, dict):
            continue
        address = str(entry.get("email") or "").strip()
        if not address:
            continue
        verified = bool(entry.get("verified"))
        if not verified:
            continue
        if entry.get("primary"):
            primary_verified = address
            break
        if not first_verified:
            first_verified = address
    chosen = primary_verified or first_verified
    return chosen, bool(chosen)
