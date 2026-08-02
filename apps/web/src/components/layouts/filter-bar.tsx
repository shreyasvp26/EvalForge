import { Cluster, cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

export type FilterBarProps = HTMLAttributes<HTMLDivElement> & {
  /** Primary search control. */
  search?: ReactNode;
  /** Filter controls (selects, toggles). */
  filters?: ReactNode;
  /** Trailing meta (result count, clear). */
  meta?: ReactNode;
};

/**
 * Search + filter chrome for collection views. Keep controls quiet and dense.
 */
export function FilterBar({ search, filters, meta, className, ...props }: FilterBarProps) {
  return (
    <div
      role="search"
      className={cn(
        "flex flex-col gap-3 rounded-[var(--ef-radius-panel)] border border-border bg-card p-3 sm:flex-row sm:items-center",
        className,
      )}
      {...props}
    >
      {search !== undefined ? <div className="min-w-0 flex-1">{search}</div> : null}
      {filters !== undefined ? <Cluster gap={2}>{filters}</Cluster> : null}
      {meta !== undefined ? <div className="shrink-0 sm:ml-auto sm:text-right">{meta}</div> : null}
    </div>
  );
}
