import { Cluster, cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

export type ToolbarProps = HTMLAttributes<HTMLDivElement> & {
  /** Leading controls (tabs, view switchers). */
  start?: ReactNode;
  /** Trailing actions (create, export). */
  end?: ReactNode;
  children?: ReactNode;
};

/**
 * Dense action row for list and detail pages.
 */
export function Toolbar({ start, end, children, className, ...props }: ToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
      {...props}
    >
      <Cluster gap={2} className="min-w-0">
        {start}
        {children}
      </Cluster>
      {end !== undefined ? (
        <Cluster gap={2} className="shrink-0 sm:justify-end">
          {end}
        </Cluster>
      ) : null}
    </div>
  );
}
