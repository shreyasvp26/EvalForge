# OAuth Integration Audit (Phase 8)

Audit of EvalForge authentication before adding Google and GitHub OAuth.

## Current architecture

| Concern | Implementation |
|---------|----------------|
| **Identity source of truth** | PostgreSQL `users.id` (`UserOrm`) |
| **Authentication** | HS256 JWT issued by API (`issue_access_token`), `sub` = user id |
| **Authorization** | `project_memberships` + `ProjectRbacAuthorization` |
| **Login** | `POST /v1/auth/login` — email/password via `IdentityPort.authenticate` |
| **Session profile** | `GET /v1/auth/me` — JWT → Actor → `IdentityPort.get_by_id` |
| **Logout** | `POST /v1/auth/logout` — stateless; client discards JWT |
| **Browser session** | JWT in `localStorage` (`evalforge.auth.token`); presence cookie `evalforge.auth=1` for Next.js middleware |
| **User creation** | Bootstrap only (`AUTH_BOOTSTRAP_*` on startup) |
| **Password storage** | scrypt hash on `users.password_hash` (NOT NULL today) |

## Integration boundaries

### Remains provider-independent

- `Actor`, JWT `sub`, RBAC, project memberships, all Application use cases
- Frontend `AuthProvider` after EvalForge JWT is issued
- Existing password login and bootstrap users

### OAuth additions (Phase 8)

- New `oauth_identities` table: `(provider, provider_user_id)` unique; optional `UNIQUE(user_id, provider)`
- Nullable `users.password_hash` for OAuth-only users
- Provider flows under `/v1/auth/{google,github}/authorize|callback`
- One-time exchange code → existing JWT issuance (no provider token as app credential)
- Signed OAuth `state` parameter with TTL and single-use enforcement

## Account-linking policy

1. Resolve by `(provider, provider_user_id)` first — always returns the linked internal user.
2. If no OAuth row exists and the provider supplies a **verified** email:
   - If a user with that email exists → link OAuth identity to that user (preserves projects/memberships).
   - Else → create a new user (no password) and link OAuth identity.
3. If email is missing or unverified → fail with actionable error (no silent account creation).
4. `(provider, provider_user_id)` uniqueness is enforced at the database; conflicts return a safe error.
5. Provider access/refresh tokens are **not** persisted.

## Callback URLs (local development)

API listens on port **8000** (`API_PORT`):

- Google: `http://localhost:8000/v1/auth/google/callback`
- GitHub: `http://localhost:8000/v1/auth/github/callback`

Web app (post-auth redirect): `http://localhost:3000/auth/callback` (`WEB_APP_URL`).
