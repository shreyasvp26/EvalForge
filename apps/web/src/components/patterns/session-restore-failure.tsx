"use client";

import { Button, Text } from "@agent-eval/ui";

export function SessionRestoreFailure({
  message,
  onRetry,
  onSignIn,
}: {
  message?: string | null;
  onRetry: () => void;
  onSignIn: () => void;
}) {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center bg-background px-4"
      role="alert"
      aria-live="assertive"
    >
      <div className="w-full max-w-sm space-y-4 rounded-[var(--ef-radius-panel)] border border-border bg-card p-5 shadow-ef-sm">
        <div className="space-y-1">
          <Text
            as="div"
            variant="caption"
            className="font-mono uppercase tracking-[0.14em] text-muted-foreground"
          >
            EvalForge
          </Text>
          <Text as="div" variant="body" className="font-medium text-foreground">
            Session couldn’t be restored
          </Text>
          <Text as="p" variant="secondary">
            {message?.trim()
              ? message
              : "Your session may have expired, or the API was unreachable."}
          </Text>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onRetry}>
            Try again
          </Button>
          <Button type="button" variant="primary" onClick={onSignIn}>
            Sign in again
          </Button>
        </div>
      </div>
    </div>
  );
}
