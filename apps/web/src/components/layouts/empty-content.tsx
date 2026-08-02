import { EmptyState, cn } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type EmptyContentProps = EmptyStateProps & {
  /** Stretch to fill the available page region. */
  fill?: boolean;
};

/**
 * Page-level empty region. Prefer domain-specific wrappers in a later milestone
 * (e.g. EmptyProjectState) that compose this primitive.
 */
export function EmptyContent({ fill = false, className, ...props }: EmptyContentProps) {
  return (
    <EmptyState
      className={cn(fill ? "min-h-[280px] justify-center" : undefined, className)}
      {...props}
    />
  );
}
