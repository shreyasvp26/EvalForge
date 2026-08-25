"use client";

import { Button } from "@agent-eval/ui";
import { useEffect, useState } from "react";

import type { OAuthProvider } from "@/lib/auth/oauth";

import { getApiBaseUrl } from "@/lib/api/client";
import { buildOAuthAuthorizeUrl } from "@/lib/auth/oauth";

interface OAuthProviders {
  google: boolean;
  github: boolean;
}

interface OAuthSignInButtonsProps {
  nextPath: string;
  disabled?: boolean;
  onProviderError?: (message: string) => void;
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5 shrink-0">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5 shrink-0 fill-current">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

const oauthButtonClassName =
  "h-11 w-full justify-start gap-3 border-[var(--ef-auth-input-border)] bg-[var(--ef-auth-input-bg)] text-[length:var(--ef-text-body)] font-medium text-foreground backdrop-blur-sm transition-[border-color,box-shadow,background-color] duration-[var(--ef-duration-normal)] hover:border-[var(--ef-auth-primary)] hover:bg-[var(--ef-auth-input-bg)] focus-visible:ring-[var(--ef-auth-primary)] focus-visible:ring-offset-0";

export function OAuthSignInButtons({
  nextPath,
  disabled = false,
  onProviderError,
}: OAuthSignInButtonsProps) {
  const [loadingProvider, setLoadingProvider] = useState<OAuthProvider | null>(null);
  const [providers, setProviders] = useState<OAuthProviders | null>(null);
  const [providersLoaded, setProvidersLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/v1/auth/providers`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          return;
        }
        const body = (await response.json()) as OAuthProviders;
        setProviders(body);
      } catch {
        // OAuth is optional — hide buttons when providers cannot be loaded.
      } finally {
        if (!controller.signal.aborted) {
          setProvidersLoaded(true);
        }
      }
    })();
    return () => {
      controller.abort();
    };
  }, []);

  if (!providersLoaded) {
    return null;
  }

  const enabled = Boolean(providers?.google ?? providers?.github);
  if (!enabled || providers === null) {
    return null;
  }

  function beginSignIn(provider: OAuthProvider) {
    onProviderError?.("");
    setLoadingProvider(provider);
    window.location.assign(buildOAuthAuthorizeUrl(provider, nextPath, getApiBaseUrl()));
  }

  return (
    <div className="space-y-3">
      {providers.google ? (
        <Button
          type="button"
          variant="ghost"
          className={oauthButtonClassName}
          disabled={disabled || loadingProvider !== null}
          loading={loadingProvider === "google"}
          onClick={() => {
            beginSignIn("google");
          }}
        >
          <GoogleIcon />
          Continue with Google
        </Button>
      ) : null}

      {providers.github ? (
        <Button
          type="button"
          variant="ghost"
          className={oauthButtonClassName}
          disabled={disabled || loadingProvider !== null}
          loading={loadingProvider === "github"}
          onClick={() => {
            beginSignIn("github");
          }}
        >
          <GitHubIcon />
          Continue with GitHub
        </Button>
      ) : null}
    </div>
  );
}
