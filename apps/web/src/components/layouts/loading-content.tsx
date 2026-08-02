import { Skeleton, Spinner, Stack, Text, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type LoadingContentProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
  /** Visual treatment: spinner (default) or skeleton blocks. */
  variant?: "spinner" | "skeleton";
  fill?: boolean;
};

/**
 * Page-level loading region. Use skeleton for structured list/detail shells.
 */
export function LoadingContent({
  label = "Loading",
  variant = "spinner",
  fill = true,
  className,
  ...props
}: LoadingContentProps) {
  if (variant === "skeleton") {
    return (
      <div
        className={cn("space-y-4", fill ? "min-h-[240px]" : undefined, className)}
        aria-busy
        aria-live="polite"
        {...props}
      >
        <span className="sr-only">{label}</span>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full max-w-md" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div
      className={cn("flex items-center justify-center", fill ? "min-h-[240px]" : "py-8", className)}
      aria-busy
      aria-live="polite"
      {...props}
    >
      <Stack gap={2} className="items-center">
        <Spinner label={label} />
        <Text variant="caption">{label}</Text>
      </Stack>
    </div>
  );
}
