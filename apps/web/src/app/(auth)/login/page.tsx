"use client";

import {
  Alert,
  ArrowRight,
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

  const displayError = formError ?? error;

  return (
    <div className="flex flex-1 flex-col justify-center px-6 py-10 sm:px-10 lg:px-14 xl:px-20">
      <div className="mx-auto w-full max-w-[22rem] motion-safe:animate-[ef-fade-up_0.5s_ease-out_both]">
        <div className="mb-8 space-y-2">
          <Heading level={1} variant="page">
            Welcome back
          </Heading>
          <Text variant="secondary">Sign in to your EvalForge workspace.</Text>
        </div>

        <form
          onSubmit={onSubmit}
          className="space-y-5 rounded-[var(--ef-radius-dialog)] border border-border bg-card p-6 shadow-ef-md"
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
              className="h-10"
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
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                disabled={submitting}
                className="h-10 pr-10"
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
                className="absolute right-1 top-1/2 -translate-y-1/2"
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
            className="h-10 w-full"
            size="lg"
            loading={submitting}
            rightIcon={ArrowRight}
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
    <div className="flex flex-1 flex-col justify-center px-6 py-10">
      <div className="mx-auto w-full max-w-[22rem] space-y-2">
        <Heading level={1} variant="page">
          Welcome back
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
