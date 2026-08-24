/** Browser session persistence for the JWT access token. */

const TOKEN_KEY = "evalforge.auth.token";
const EXPIRES_AT_KEY = "evalforge.auth.expires_at";
const SESSION_COOKIE = "evalforge.auth";

function writeSessionCookie(maxAgeSeconds: number): void {
  const maxAge = Math.max(60, Math.floor(maxAgeSeconds));
  document.cookie = `${SESSION_COOKIE}=1; Path=/; Max-Age=${String(maxAge)}; SameSite=Lax`;
}

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
  writeSessionCookie(expiresInSeconds);
}

/**
 * Re-align the middleware presence cookie with localStorage.
 * A JWT can outlive / lose the cookie (cleared site data, expired Max-Age,
 * privacy tools). Without this, GuestOnly redirects to `/` and middleware
 * bounces back to `/login`, leaving a permanent dark "Redirecting" overlay.
 */
export function syncSessionCookie(): void {
  if (typeof window === "undefined") return;
  try {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (!token) {
      document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
      return;
    }
    const expiresAt = Number(window.localStorage.getItem(EXPIRES_AT_KEY) ?? "0");
    if (expiresAt > Date.now()) {
      writeSessionCookie((expiresAt - Date.now()) / 1000);
      return;
    }
    writeSessionCookie(60);
  } catch {
    // Ignore quota / private-mode cookie failures; auth state still lives in memory.
  }
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(EXPIRES_AT_KEY);
  } catch {
    // Ignore quota / private-mode failures.
  }
  try {
    document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  } catch {
    // Ignore cookie write failures.
  }
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
