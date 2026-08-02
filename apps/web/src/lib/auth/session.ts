/** Browser session persistence for the JWT access token. */

const TOKEN_KEY = "evalforge.auth.token";
const EXPIRES_AT_KEY = "evalforge.auth.expires_at";
const SESSION_COOKIE = "evalforge.auth";

export function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (!token) return null;
    const expiresAt = Number(window.localStorage.getItem(EXPIRES_AT_KEY) ?? "0");
    if (expiresAt > 0 && Date.now() >= expiresAt) {
      clearAccessToken();
      return null;
    }
    return token;
  } catch {
    return null;
  }
}

export function persistAccessToken(token: string, expiresInSeconds: number): void {
  if (typeof window === "undefined") return;
  const expiresAt = Date.now() + expiresInSeconds * 1000;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(EXPIRES_AT_KEY, String(expiresAt));
  // Presence cookie for Next.js middleware route gating (not the credential).
  const maxAge = Math.max(60, expiresInSeconds);
  document.cookie = `${SESSION_COOKIE}=1; Path=/; Max-Age=${String(maxAge)}; SameSite=Lax`;
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(EXPIRES_AT_KEY);
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

/** Epoch ms when the stored access token expires, or null if unknown/absent. */
export function readTokenExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(EXPIRES_AT_KEY);
    if (!raw) return null;
    const value = Number(raw);
    if (!Number.isFinite(value) || value <= 0) return null;
    return value;
  } catch {
    return null;
  }
}

export function hasSessionCookie(cookieHeader: string | null | undefined): boolean {
  if (!cookieHeader) return false;
  return cookieHeader.split(";").some((part) => part.trim().startsWith(`${SESSION_COOKIE}=`));
}
