"use client";

import { Button, Text } from "@agent-eval/ui";

import { ErrorContent } from "@/components/layouts/error-content";

export default function ShellError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-lg flex-col justify-center px-6 py-16">
      <ErrorContent
        fill
        title="Something went wrong"
        description={
          error.message
            ? error.message
            : "An unexpected error interrupted this view. You can retry or return to Overview."
        }
        action={
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={reset}>
              Try again
            </Button>
            <Button asChild variant="outline">
              <a href="/">Back to Overview</a>
            </Button>
          </div>
        }
      />
      {error.digest ? (
        <Text variant="caption" className="mt-4 font-mono">
          Digest {error.digest}
        </Text>
      ) : null}
    </div>
  );
}
