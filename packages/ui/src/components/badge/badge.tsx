import { cva } from "class-variance-authority";

import { cn } from "../../lib/cn";

import type { VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2 py-0.5 text-[length:var(--ef-text-caption)] leading-[var(--ef-text-caption-leading)] font-medium",
  {
    variants: {
      status: {
        neutral: "bg-muted text-muted-foreground",
        success: "bg-success-muted text-success",
        warning: "bg-warning-muted text-warning",
        danger: "bg-danger-muted text-danger",
        running: "bg-running-muted text-running",
        queued: "bg-queued-muted text-queued",
        cancelled: "bg-cancelled-muted text-cancelled",
        completed: "bg-completed-muted text-completed",
        grading: "bg-grading-muted text-grading",
      },
    },
    defaultVariants: {
      status: "neutral",
    },
  },
);

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, status, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ status }), className)} {...props} />;
}

export { badgeVariants };
