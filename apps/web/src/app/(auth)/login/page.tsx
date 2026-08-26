"use client";

import {
  Alert,
  Button,
  Eye,
  EyeOff,
  Heading,
  IconButton,
  Input,
  Label,
  Text,
} from "@agent-eval/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { z } from "zod";

import { OAuthSignInButtons } from "@/components/auth/oauth-sign-in-buttons";
import { InlineError } from "@/components/patterns/inline-error";
import { readUserPreferences } from "@/features/settings/preferences-store";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";
import { GuestOnly } from "@/lib/auth/guest-only";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

function safeNextPath(raw: string | null): string {
  if (!raw) return readUserPreferences().landingPage;
  if (!raw.startsWith("/") || raw.startsWith("//")) return readUserPreferences().landingPage;
  if (raw.startsWith("/login")) return readUserPreferences().landingPage;
  return raw;
}

const authInputClassName =
  "h-11 border-[var(--ef-auth-input-border)] bg-[var(--ef-auth-input-bg)] backdrop-blur-sm placeholder:text-muted-foreground/70 focus-visible:ring-[var(--ef-auth-primary)] focus-visible:ring-offset-0";

function LoginForm() {
  const { login, error, clearError } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));
  const oauthError = searchParams.get("error");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
  }>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function onSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setFormError(null);

    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      const nextErrors: { email?: string; password?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "email" || key === "password") {
          nextErrors[key] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    setSubmitting(true);
    void (async () => {
      try {
        await login(parsed.data.email, parsed.data.password);
        router.replace(nextPath);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Sign in failed. Please try again.");
        }
      } finally {
        setSubmitting(false);
      }
    })();
  }

  const displayError = formError ?? error ?? oauthError;

  return (
    <div className="mx-auto w-full max-w-[420px] motion-safe:animate-[ef-fade-up_0.8s_ease-out_0.2s_both]">
      <div
        className="rounded-[var(--ef-radius-dialog)] border border-[var(--ef-auth-card-border)] p-8 shadow-[0_24px_80px_rgb(0_0_0/0.35),inset_0_1px_0_var(--ef-auth-card-highlight)] backdrop-blur-xl sm:p-9"
        style={{ background: "var(--ef-auth-card-bg)" }}
      >
        <div className="mb-8 space-y-2">
          <Heading level={1} variant="page" className="text-[length:var(--ef-text-section)]">
            Welcome back
          </Heading>
          <Text variant="secondary">Sign in to your EvalForge workspace.</Text>
        </div>

        <form onSubmit={onSubmit} className="space-y-6" noValidate>
          {displayError ? (
            <Alert variant="danger" title="Sign in failed">
              {displayError}
            </Alert>
          ) : null}

          <OAuthSignInButtons
            nextPath={nextPath}
            disabled={submitting}
            onProviderError={(message) => {
              if (message) {
                setFormError(message);
              }
            }}
          />

          <div className="relative py-1">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-[var(--ef-auth-input-border)]" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-transparent px-3 text-xs uppercase tracking-wide text-muted-foreground">
                or continue with email
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-muted-foreground">
              Email
            </Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              autoFocus
              value={email}
              disabled={submitting}
              className={authInputClassName}
              onChange={(event) => {
                setEmail(event.target.value);
                if (fieldErrors.email) {
                  setFieldErrors((current) => {
                    const next = { ...current };
                    delete next.email;
                    return next;
                  });
                }
              }}
              aria-invalid={fieldErrors.email ? true : undefined}
              aria-describedby={fieldErrors.email ? "email-error" : undefined}
            />
            {fieldErrors.email ? (
              <InlineError id="email-error">{fieldErrors.email}</InlineError>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-muted-foreground">
              Password
            </Label>
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                disabled={submitting}
                className={`${authInputClassName} pr-11`}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((current) => {
                      const next = { ...current };
                      delete next.password;
                      return next;
                    });
                  }
                }}
                aria-invalid={fieldErrors.password ? true : undefined}
                aria-describedby={fieldErrors.password ? "password-error" : undefined}
              />
              <IconButton
                icon={showPassword ? EyeOff : Eye}
                label={showPassword ? "Hide password" : "Show password"}
                size="sm"
                type="button"
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => {
                  setShowPassword((value) => !value);
                }}
              />
            </div>
            {fieldErrors.password ? (
              <InlineError id="password-error">{fieldErrors.password}</InlineError>
            ) : null}
          </div>

          <Button
            type="submit"
            variant="ghost"
            className="ef-auth-primary-fill h-11 w-full text-[length:var(--ef-text-body)] font-semibold shadow-[0_4px_24px_var(--ef-auth-primary-glow)] transition-[filter,box-shadow] duration-[var(--ef-duration-normal)] hover:bg-transparent"
            size="lg"
            loading={submitting}
          >
            Sign in
          </Button>
        </form>
      </div>
    </div>
  );
}

function LoginFormFallback() {
  return (
    <div className="mx-auto w-full max-w-[420px] space-y-2 px-6">
      <Heading level={1} variant="page">
        Welcome back
      </Heading>
      <Text variant="secondary">Loading sign-in form…</Text>
    </div>
  );
}

export default function LoginPage() {
  return (
    <GuestOnly>
      <Suspense fallback={<LoginFormFallback />}>
        <LoginForm />
      </Suspense>
    </GuestOnly>
  );
}
