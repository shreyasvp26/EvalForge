import { Skeleton, Text, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type GlobalLoadingProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
};

/**
 * Full-viewport overlay for rare blocking work (boot, hard navigations).
 * Prefer PageSkeleton / TableSkeleton for in-page loads.
 */
export function GlobalLoading({
  label = "Loading EvalForge",
  className,
  ...props
}: GlobalLoadingProps) {
  return (
    <div
      className={cn(
        // Solid background + visible card — avoid a dark translucent wash that
        // looks like a hung black screen when auth is resolving.
        "fixed inset-0 z-[var(--ef-z-overlay)] flex items-center justify-center bg-background",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy
      {...props}
    >
      <div className="flex w-56 flex-col gap-3 rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-2 w-[80%]" />
        <Text variant="caption">{label}</Text>
      </div>
    </div>
  );
}
