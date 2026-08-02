import { AlertCircle, Icon, Text, cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

export type InlineErrorProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  children: ReactNode;
  /** Compact for field-level validation under an input. */
  density?: "field" | "block";
};

/**
 * Inline / field-adjacent error. Use ErrorContent for full-page failures.
 */
export function InlineError({
  title,
  children,
  density = "field",
  className,
  ...props
}: InlineErrorProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex gap-2 text-danger",
        density === "block"
          ? "rounded-[var(--ef-radius-control)] border border-danger/30 bg-danger-muted px-3 py-2"
          : "items-start",
        className,
      )}
      {...props}
    >
      <Icon icon={AlertCircle} size="sm" className="mt-0.5 shrink-0" aria-hidden />
      <div className="min-w-0 space-y-0.5">
        {title !== undefined ? (
          <Text as="div" variant="caption" className="font-medium text-inherit">
            {title}
          </Text>
        ) : null}
        <Text as="div" variant="caption" className="text-inherit opacity-90">
          {children}
        </Text>
      </div>
    </div>
  );
}
