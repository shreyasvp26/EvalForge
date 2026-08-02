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
import type { ReactNode } from "react";

import { fetchCurrentUser, loginRequest, logoutRequest } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { clearAccessToken, persistAccessToken, readAccessToken } from "@/lib/auth/session";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  token: string | null;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    const existing = readAccessToken();
    if (!existing) {
      setStatus("unauthenticated");
      return;
    }

    void (async () => {
      try {
        const profile = await fetchCurrentUser(existing);
        if (cancelledRef.current) return;
        setToken(existing);
        setUser(profile);
        setStatus("authenticated");
      } catch {
        if (cancelledRef.current) return;
        clearAccessToken();
        setToken(null);
        setUser(null);
        setStatus("unauthenticated");
      }
    })();

    return () => {
      cancelledRef.current = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const result = await loginRequest(email, password);
      persistAccessToken(result.access_token, result.expires_in);
      setToken(result.access_token);
      setUser(result.user);
      setStatus("authenticated");
    } catch (cause) {
      clearAccessToken();
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
      clearAccessToken();
      setToken(null);
      setUser(null);
      setStatus("unauthenticated");
      setError(null);
    }
  }, [token]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      token,
      error,
      login,
      logout,
      clearError,
    }),
    [status, user, token, error, login, logout, clearError],
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
