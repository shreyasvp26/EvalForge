import { cn } from "../../lib/cn";

import type { HTMLAttributes } from "react";

export type SkeletonProps = HTMLAttributes<HTMLDivElement>;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-[var(--ef-radius-control)] bg-muted", className)}
      aria-hidden
      {...props}
    />
  );
}
