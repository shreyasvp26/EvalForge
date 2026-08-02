import { Skeleton, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type TableSkeletonProps = HTMLAttributes<HTMLDivElement> & {
  columns?: number;
  rows?: number;
  withToolbar?: boolean;
};

/**
 * Table-shaped skeleton that matches DataGrid density — avoids layout jump on load.
 */
export function TableSkeleton({
  columns = 4,
  rows = 6,
  withToolbar = true,
  className,
  ...props
}: TableSkeletonProps) {
  return (
    <div className={cn("space-y-3", className)} aria-busy aria-live="polite" {...props}>
      <span className="sr-only">Loading table</span>
      {withToolbar ? (
        <div className="flex flex-col gap-3 sm:flex-row">
          <Skeleton className="h-9 flex-1" />
          <Skeleton className="h-9 w-28" />
        </div>
      ) : null}
      <div className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border">
        <div className="flex gap-3 border-b border-border bg-muted/60 px-3 py-3">
          {Array.from({ length: columns }).map((_, index) => (
            <Skeleton key={`h-${String(index)}`} className="h-3 flex-1" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div
            key={`r-${String(rowIndex)}`}
            className="flex gap-3 border-b border-border px-3 py-3 last:border-0"
          >
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton key={`c-${String(rowIndex)}-${String(colIndex)}`} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
