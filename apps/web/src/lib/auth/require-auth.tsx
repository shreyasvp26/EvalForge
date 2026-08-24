"use client";

import { Text } from "@agent-eval/ui";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { ReactNode } from "react";

import { GlobalLoading } from "@/components/patterns/global-loading";
import { useAuth } from "@/lib/auth/auth-provider";
import { syncSessionCookie } from "@/lib/auth/session";

/**
 * Gates authenticated product routes. Shows a boot overlay while the
 * session is restored, then redirects guests to /login.
 *
 * Never stay on an opaque dark full-viewport overlay indefinitely: cookie/JWT
 * mismatch must resolve to authenticated UI or /login.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      syncSessionCookie();
      return;
    }
    if (status === "unauthenticated") {
      const next = `${window.location.pathname}${window.location.search}`;
      const params = new URLSearchParams();
      if (next && next !== "/" && next !== "/login") {
        params.set("next", next);
      }
      const query = params.toString();
      router.replace(query ? `/login?${query}` : "/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return <GlobalLoading label="Restoring session" />;
  }

  if (status !== "authenticated") {
    // Keep a light, intentional redirect state — not a dark blocking overlay.
    return (
      <div
        className="flex min-h-dvh items-center justify-center bg-background px-4"
        role="status"
        aria-live="polite"
      >
        <Text variant="secondary">Redirecting to sign in…</Text>
      </div>
    );
  }

  return children;
}
