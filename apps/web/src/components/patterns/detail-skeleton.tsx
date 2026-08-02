import { Skeleton, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type DetailSkeletonProps = HTMLAttributes<HTMLDivElement> & {
  withInspector?: boolean;
};

/**
 * Detail page skeleton with optional inspector column — keeps chrome stable.
 */
export function DetailSkeleton({ withInspector = true, className, ...props }: DetailSkeletonProps) {
  return (
    <div
      className={cn("flex min-h-[320px] gap-0", className)}
      aria-busy
      aria-live="polite"
      {...props}
    >
      <span className="sr-only">Loading detail</span>
      <div className="min-w-0 flex-1 space-y-6 px-1 py-1">
        <div className="space-y-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-full max-w-lg" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
      {withInspector ? (
        <div className="hidden w-[320px] shrink-0 space-y-4 border-l border-border p-4 md:block">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : null}
    </div>
  );
}
