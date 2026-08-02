"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { ReactNode } from "react";

import { GlobalLoading } from "@/components/patterns/global-loading";
import { useAuth } from "@/lib/auth/auth-provider";

/**
 * Gates authenticated product routes. Shows a boot overlay while the
 * session is restored, then redirects guests to /login.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
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
    return <GlobalLoading label="Redirecting to sign in" />;
  }

  return children;
}
