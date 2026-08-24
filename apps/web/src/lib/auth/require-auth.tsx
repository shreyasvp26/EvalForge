"use client";

import { Button, Text } from "@agent-eval/ui";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { ReactNode } from "react";

import { GlobalLoading } from "@/components/patterns/global-loading";
import { SessionRestoreFailure } from "@/components/patterns/session-restore-failure";
import { useAuth } from "@/lib/auth/auth-provider";
import { syncSessionCookie } from "@/lib/auth/session";

/**
 * Gates authenticated product routes.
 *
 * States:
 * - restoring → branded boot panel (never an indefinite black void)
 * - restore_failed → recoverable CTA
 * - unauthenticated → redirect to /login
 * - authenticated → children
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status, restoreError, dismissRestoreFailure, retryRestore } = useAuth();
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

  if (status === "restoring") {
    return <GlobalLoading label="Restoring session" />;
  }

  if (status === "restore_failed") {
    return (
      <SessionRestoreFailure
        message={restoreError}
        onRetry={() => {
          void retryRestore();
        }}
        onSignIn={() => {
          dismissRestoreFailure();
          router.replace("/login");
        }}
      />
    );
  }

  if (status !== "authenticated") {
    return (
      <div
        className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-background px-4"
        role="status"
        aria-live="polite"
      >
        <Text
          variant="caption"
          className="font-mono uppercase tracking-[0.14em] text-muted-foreground"
        >
          EvalForge
        </Text>
        <Text variant="secondary">Redirecting to sign in…</Text>
        <Button asChild variant="outline" size="sm">
          <a href="/login">Sign in</a>
        </Button>
      </div>
    );
  }

  return children;
}
