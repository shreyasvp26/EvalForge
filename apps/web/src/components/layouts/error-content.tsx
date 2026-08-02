import { ErrorState, cn } from "@agent-eval/ui";

import type { ErrorStateProps } from "@agent-eval/ui";

export type ErrorContentProps = ErrorStateProps & {
  fill?: boolean;
};

/**
 * Page-level error region. Keep copy specific and actionable at the call site.
 */
export function ErrorContent({ fill = false, className, ...props }: ErrorContentProps) {
  return (
    <ErrorState
      className={cn(fill ? "min-h-[280px] justify-center" : undefined, className)}
      {...props}
    />
  );
}
