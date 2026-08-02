"use client";

import { Button, Text } from "@agent-eval/ui";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-dvh bg-white text-neutral-900 antialiased">
        <div className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center gap-4 px-6 py-16">
          <Text as="div" variant="body" className="text-xl font-medium">
            EvalForge could not recover
          </Text>
          <Text variant="secondary">
            {error.message ||
              "A critical rendering error occurred. Retry to reload the application."}
          </Text>
          {error.digest ? (
            <Text variant="caption" className="font-mono">
              Digest {error.digest}
            </Text>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={reset}>
              Try again
            </Button>
            <Button asChild variant="outline">
              <a href="/">Back to Overview</a>
            </Button>
          </div>
        </div>
      </body>
    </html>
  );
}
