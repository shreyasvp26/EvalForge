"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { AuthUser } from "@/lib/api/auth";
import type { AuthStatus } from "@/lib/auth/auth-types";
import type { ReactNode } from "react";

import { fetchCurrentUser, loginRequest, logoutRequest } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { AUTH_RESTORE_TIMEOUT_MS } from "@/lib/auth/constants";
import { resolveSessionRestore } from "@/lib/auth/resolve-session-restore";
import {
  clearAccessToken,
  persistAccessToken,
  readAccessToken,
  syncSessionCookie,
} from "@/lib/auth/session";

export type { AuthStatus } from "./auth-types";
export { AUTH_RESTORE_TIMEOUT_MS } from "@/lib/auth/constants";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  token: string | null;
  error: string | null;
  restoreError: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  /** Clear local session and move to unauthenticated (recovery CTA). */
  dismissRestoreFailure: () => void;
  /** Retry /v1/auth/me with the stored token, if any. */
  retryRestore: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function safeClearSession(): void {
  try {
    clearAccessToken();
  } catch {
    // Private mode / blocked storage must not trap auth in "restoring".
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("restoring");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const cancelledRef = useRef(false);
  const generationRef = useRef(0);

  const finishUnauthenticated = useCallback(() => {
    safeClearSession();
    setToken(null);
    setUser(null);
    setRestoreError(null);
    setStatus("unauthenticated");
  }, []);

  const finishRestoreFailed = useCallback((message: string) => {
    setRestoreError(message);
    setStatus("restore_failed");
  }, []);

  const restoreWithToken = useCallback(
    async (existing: string, generation: number) => {
      // Absolute wall clock — resolves even if fetch ignores AbortSignal.
      const wallTimer = window.setTimeout(() => {
        if (cancelledRef.current || generationRef.current !== generation) return;
        finishRestoreFailed("Your session could not be restored in time.");
      }, AUTH_RESTORE_TIMEOUT_MS + 250);

      try {
        const outcome = await resolveSessionRestore({
          token: existing,
          fetchMe: (token, signal) => fetchCurrentUser(token, { signal }),
        });
        if (cancelledRef.current || generationRef.current !== generation) return;

        if (outcome.status === "authenticated") {
          syncSessionCookie();
          setToken(existing);
          setUser(outcome.profile as AuthUser);
          setRestoreError(null);
          setStatus("authenticated");
          return;
        }
        if (outcome.status === "unauthenticated") {
          finishUnauthenticated();
          return;
        }
        finishRestoreFailed(outcome.message);
      } finally {
        window.clearTimeout(wallTimer);
      }
    },
    [finishRestoreFailed, finishUnauthenticated],
  );

  useEffect(() => {
    cancelledRef.current = false;
    const generation = ++generationRef.current;

    let existing: string | null = null;
    try {
      existing = readAccessToken();
    } catch {
      existing = null;
    }

    if (!existing) {
      // Drop a leftover presence cookie so middleware stops treating this
      // browser as signed-in when localStorage has no usable token.
      finishUnauthenticated();
      return;
    }

    void restoreWithToken(existing, generation);

    return () => {
      cancelledRef.current = true;
    };
  }, [finishUnauthenticated, restoreWithToken]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setRestoreError(null);
    try {
      const result = await loginRequest(email, password);
      persistAccessToken(result.access_token, result.expires_in);
      setToken(result.access_token);
      setUser(result.user);
      setStatus("authenticated");
    } catch (cause) {
      safeClearSession();
      setToken(null);
      setUser(null);
      setStatus("unauthenticated");
      if (cause instanceof ApiError) {
        setError(cause.message);
      } else {
        setError("Sign in failed. Please try again.");
      }
      throw cause;
    }
  }, []);

  const logout = useCallback(async () => {
    const current = token ?? readAccessToken();
    try {
      if (current) {
        await logoutRequest(current);
      }
    } catch {
      // Always clear local session even if the network call fails.
    } finally {
      safeClearSession();
      setToken(null);
      setUser(null);
      setStatus("unauthenticated");
      setError(null);
      setRestoreError(null);
    }
  }, [token]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const dismissRestoreFailure = useCallback(() => {
    safeClearSession();
    setToken(null);
    setUser(null);
    setRestoreError(null);
    setStatus("unauthenticated");
  }, []);

  const retryRestore = useCallback(async () => {
    let existing: string | null = null;
    try {
      existing = readAccessToken();
    } catch {
      existing = null;
    }
    if (!existing) {
      finishUnauthenticated();
      return;
    }
    setRestoreError(null);
    setStatus("restoring");
    const generation = ++generationRef.current;
    await restoreWithToken(existing, generation);
  }, [finishUnauthenticated, restoreWithToken]);

  const value = useMemo(
    () => ({
      status,
      user,
      token,
      error,
      restoreError,
      login,
      logout,
      clearError,
      dismissRestoreFailure,
      retryRestore,
    }),
    [
      status,
      user,
      token,
      error,
      restoreError,
      login,
      logout,
      clearError,
      dismissRestoreFailure,
      retryRestore,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}

/** @deprecated Prefer AuthStatus; kept for transitional imports. */
export type AuthStatusLegacy = "loading" | "authenticated" | "unauthenticated";
