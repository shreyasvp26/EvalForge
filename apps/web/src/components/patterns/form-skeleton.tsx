import { Skeleton, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type FormSkeletonProps = HTMLAttributes<HTMLDivElement> & {
  fields?: number;
};

/**
 * Form layout skeleton — labels + controls without jumping when fields hydrate.
 */
export function FormSkeleton({ fields = 4, className, ...props }: FormSkeletonProps) {
  return (
    <div className={cn("max-w-lg space-y-5", className)} aria-busy aria-live="polite" {...props}>
      <span className="sr-only">Loading form</span>
      {Array.from({ length: fields }).map((_, index) => (
        <div key={String(index)} className="space-y-2">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-9 w-full" />
        </div>
      ))}
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-20" />
      </div>
    </div>
  );
}
