# OAuth authentication (Phase 8)

EvalForge supports Google and GitHub OAuth as additional sign-in methods. Provider
identities are stored in `oauth_identities` and mapped to the internal `users`
table. Authorization continues to use the internal user id (JWT `sub`).

## Architecture

```
Browser → GET /v1/auth/{provider}/authorize
       → Provider consent
       → GET /v1/auth/{provider}/callback (API)
       → one-time exchange code
       → GET /auth/callback (Web)
       → POST /v1/auth/oauth/exchange
       → EvalForge JWT (same as password login)
```

Provider access tokens are **not** stored. OAuth `state` is single-use with a
short TTL. The web callback receives a one-time exchange code — not the JWT.

## Account linking

1. Match `(provider, provider_user_id)` first.
2. If new, require a **verified** provider email.
3. If email matches an existing user, link the OAuth identity to that user.
4. One OAuth identity per provider per user (`UNIQUE(user_id, provider)`).

Password login continues to work for users with a `password_hash`.

## Environment variables

```bash
WEB_APP_URL=http://localhost:3000

OAUTH_GOOGLE_ENABLED=true
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/v1/auth/google/callback

OAUTH_GITHUB_ENABLED=true
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/v1/auth/github/callback
```

## Google Cloud setup

1. Create an OAuth 2.0 Client ID (Web application).
2. Authorized redirect URI: `http://localhost:8000/v1/auth/google/callback`
3. Copy Client ID and Client Secret into `.env`.
4. Enable the Google+ / People API if required by your project.

## GitHub setup

1. Settings → Developer settings → OAuth Apps → New OAuth App.
2. Authorization callback URL: `http://localhost:8000/v1/auth/github/callback`
3. Copy Client ID and generate a Client Secret.
4. Requested scopes: `read:user`, `user:email` (configured server-side).

## Local development

- API: `http://localhost:8000` (`API_PORT`)
- Web: `http://localhost:3000` (`WEB_PORT`)
- Use `localhost` consistently in redirect URIs (not mixed with `127.0.0.1`).

## Disabling a provider

Set `OAUTH_GOOGLE_ENABLED=false` or `OAUTH_GITHUB_ENABLED=false`. The login page
hides disabled providers automatically via `GET /v1/auth/providers`.

## Manual smoke test

With credentials configured:

1. Open `/login` → **Continue with Google** or **Continue with GitHub**
2. Complete provider sign-in
3. Confirm redirect to overview and `GET /v1/auth/me` returns the expected user
4. Sign out and sign in again — same internal user id, no duplicate account

## Troubleshooting

| Symptom                 | Check                                                          |
| ----------------------- | -------------------------------------------------------------- |
| Provider buttons hidden | `GET /v1/auth/providers`, env flags, client id/secret/redirect |
| `redirect_uri_mismatch` | Exact match with provider console (scheme, host, path)         |
| Missing GitHub email    | Primary email private — app reads `/user/emails` verified list |
| Invalid OAuth state     | Clock skew, expired flow (>10 min), or replayed callback       |
