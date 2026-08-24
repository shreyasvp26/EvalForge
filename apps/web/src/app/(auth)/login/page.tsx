"use client";

import { Alert, Button, Heading, Input, Label, Text } from "@agent-eval/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { z } from "zod";

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

function LoginForm() {
  const { login, error, clearError } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  const displayError = formError ?? error;

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12">
      <div className="mb-8 space-y-3">
        <div className="space-y-1">
          <Text variant="caption" className="font-mono tracking-[0.16em] uppercase text-foreground">
            EvalForge
          </Text>
          <Text variant="caption" className="text-muted-foreground">
            Evaluation control plane
          </Text>
        </div>
        <Heading level={1} variant="page">
          Sign in
        </Heading>
        <Text variant="secondary">
          Continue to your workspace to launch evaluations and inspect execution.
        </Text>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-[var(--ef-radius-panel)] border border-border bg-card p-5 shadow-ef-sm"
        noValidate
      >
        {displayError ? (
          <Alert variant="danger" title="Sign in failed">
            {displayError}
          </Alert>
        ) : null}

        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoFocus
            value={email}
            disabled={submitting}
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

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            disabled={submitting}
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
          {fieldErrors.password ? (
            <InlineError id="password-error">{fieldErrors.password}</InlineError>
          ) : null}
        </div>

        <Button type="submit" className="w-full" loading={submitting}>
          Sign in
        </Button>
      </form>
    </div>
  );
}

function LoginFormFallback() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12">
      <div className="mb-8 space-y-2">
        <Text variant="caption" className="tracking-[0.08em] uppercase">
          EvalForge
        </Text>
        <Heading level={1} variant="page">
          Sign in
        </Heading>
        <Text variant="secondary">Loading sign-in form…</Text>
      </div>
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
