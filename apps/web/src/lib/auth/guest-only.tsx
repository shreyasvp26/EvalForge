"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { ReactNode } from "react";

import { readUserPreferences } from "@/features/settings/preferences-store";
import { useAuth } from "@/lib/auth/auth-provider";
import { syncSessionCookie } from "@/lib/auth/session";

/**
 * Redirects authenticated users away from guest-only routes (login).
 *
 * Keep the guest UI mounted while redirecting — replacing it with a dark
 * full-viewport overlay made a missing session cookie look like a black
 * screen when middleware bounced `/` back to `/login`.
 */
export function GuestOnly({ children, redirectTo }: { children: ReactNode; redirectTo?: string }) {
  const { status } = useAuth();
  const router = useRouter();
  const target = redirectTo ?? readUserPreferences().landingPage;

  useEffect(() => {
    if (status !== "authenticated") return;
    syncSessionCookie();
    router.replace(target);
  }, [status, router, target]);

  return children;
}
