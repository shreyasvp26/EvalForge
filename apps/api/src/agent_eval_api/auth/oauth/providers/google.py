"""Google OAuth 2.0 / OpenID Connect provider."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from agent_eval_application.ports.oauth_identity import OAuthProviderIdentity

from agent_eval_api.auth.oauth.providers.base import OAuthAuthorizationRequest


@dataclass(slots=True)
class GoogleOAuthProvider:
    client_id: str
    client_secret: str
    redirect_uri: str
    provider: str = "google"

    def build_authorization_url(
        self, *, state: str, nonce: str
    ) -> OAuthAuthorizationRequest:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
        return OAuthAuthorizationRequest(
            authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        )

    async def exchange_code(self, *, code: str, nonce: str) -> OAuthProviderIdentity:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            id_token = token_payload.get("id_token")
            access_token = token_payload.get("access_token")
            if not access_token:
                raise ValueError("Google token response missing access_token")

            userinfo_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            profile = userinfo_response.json()

        subject = str(profile.get("sub") or "").strip()
        email = str(profile.get("email") or "").strip()
        if not subject:
            raise ValueError("Google profile missing subject")
        if not email:
            raise ValueError("Google profile missing email")

        email_verified = bool(profile.get("email_verified"))
        display_name = str(profile.get("name") or email).strip()

        if id_token and nonce:
            # Nonce validation is best-effort when id_token is present.
            _validate_google_nonce(id_token, nonce)

        return OAuthProviderIdentity(
            provider="google",
            provider_user_id=subject,
            email=email,
            email_verified=email_verified,
            display_name=display_name,
        )


def _validate_google_nonce(id_token: str, expected_nonce: str) -> None:
    import base64
    import json

    parts = id_token.split(".")
    if len(parts) < 2:
        return
    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    decoded = base64.urlsafe_b64decode(payload_segment + padding)
    claims = json.loads(decoded.decode("utf-8"))
    token_nonce = claims.get("nonce")
    if token_nonce and token_nonce != expected_nonce:
        raise ValueError("Google ID token nonce mismatch")
