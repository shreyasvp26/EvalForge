"use client";

import { Alert, Heading, Text } from "@agent-eval/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { readUserPreferences } from "@/features/settings/preferences-store";
import { useAuth } from "@/lib/auth/auth-provider";
import { GuestOnly } from "@/lib/auth/guest-only";

function safeNextPath(raw: string | null): string {
  if (!raw) return readUserPreferences().landingPage;
  if (!raw.startsWith("/") || raw.startsWith("//")) return readUserPreferences().landingPage;
  if (raw.startsWith("/login") || raw.startsWith("/auth/callback")) {
    return readUserPreferences().landingPage;
  }
  return raw;
}

function OAuthCallbackForm() {
  const { completeOAuthSession } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const oauthError = searchParams.get("error");
    const nextPath = safeNextPath(searchParams.get("next"));

    if (oauthError) {
      setError(oauthError);
      return;
    }
    if (!code) {
      setError("Sign in could not be completed. Please try again.");
      return;
    }

    void (async () => {
      try {
        await completeOAuthSession(code);
        router.replace(nextPath);
      } catch (cause) {
        if (cause instanceof Error && cause.message) {
          setError(cause.message);
        } else {
          setError("Sign in failed. Please try again.");
        }
      }
    })();
  }, [completeOAuthSession, router, searchParams]);

  if (error) {
    return (
      <div className="mx-auto w-full max-w-[420px] space-y-4">
        <Alert variant="danger" title="Sign in failed">
          {error}
        </Alert>
        <Text variant="secondary">
          Return to{" "}
          <a href="/login" className="underline underline-offset-4">
            sign in
          </a>
          .
        </Text>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[420px] space-y-2">
      <Heading level={1} variant="page">
        Completing sign in
      </Heading>
      <Text variant="secondary">Securing your EvalForge session…</Text>
    </div>
  );
}

function OAuthCallbackFallback() {
  return (
    <div className="mx-auto w-full max-w-[420px] space-y-2">
      <Heading level={1} variant="page">
        Completing sign in
      </Heading>
      <Text variant="secondary">Loading…</Text>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <GuestOnly>
      <Suspense fallback={<OAuthCallbackFallback />}>
        <OAuthCallbackForm />
      </Suspense>
    </GuestOnly>
  );
}
