import { Skeleton, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type PageSkeletonProps = HTMLAttributes<HTMLDivElement> & {
  /** Show an actions cluster in the header. */
  withActions?: boolean;
};

/**
 * Preserves page header + body layout while content loads.
 * Prefer this over a centered spinner for route transitions.
 */
export function PageSkeleton({ withActions = true, className, ...props }: PageSkeletonProps) {
  return (
    <div className={cn("space-y-8", className)} aria-busy aria-live="polite" {...props}>
      <span className="sr-only">Loading page</span>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-4 w-full max-w-md" />
        </div>
        {withActions ? (
          <div className="flex gap-2">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-28" />
          </div>
        ) : null}
      </div>
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  );
}
