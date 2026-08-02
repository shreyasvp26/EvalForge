"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { ReactNode } from "react";

import { GlobalLoading } from "@/components/patterns/global-loading";
import { readUserPreferences } from "@/features/settings/preferences-store";
import { useAuth } from "@/lib/auth/auth-provider";

/**
 * Redirects authenticated users away from guest-only routes (login).
 */
export function GuestOnly({ children, redirectTo }: { children: ReactNode; redirectTo?: string }) {
  const { status } = useAuth();
  const router = useRouter();
  const target = redirectTo ?? readUserPreferences().landingPage;

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(target);
    }
  }, [status, router, target]);

  if (status === "loading") {
    return <GlobalLoading label="Checking session" />;
  }

  if (status === "authenticated") {
    return <GlobalLoading label="Redirecting" />;
  }

  return children;
}
