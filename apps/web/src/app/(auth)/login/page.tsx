"use client";

import { Alert, Button, FadeIn, Heading, Input, Label, Text } from "@agent-eval/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { z } from "zod";

import { GlobalLoading } from "@/components/patterns/global-loading";
import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";
import { GuestOnly } from "@/lib/auth/guest-only";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

function safeNextPath(raw: string | null): string {
  if (!raw) return "/";
  if (!raw.startsWith("/") || raw.startsWith("//")) return "/";
  if (raw.startsWith("/login")) return "/";
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
    <FadeIn className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12">
      <div className="mb-8 space-y-2">
        <Text variant="caption" className="tracking-[0.08em] uppercase">
          EvalForge
        </Text>
        <Heading level={1} variant="page">
          Sign in
        </Heading>
        <Text variant="secondary">
          Use your EvalForge credentials to continue to the workspace.
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
    </FadeIn>
  );
}

export default function LoginPage() {
  return (
    <GuestOnly>
      <Suspense fallback={<GlobalLoading label="Loading sign in" />}>
        <LoginForm />
      </Suspense>
    </GuestOnly>
  );
}
