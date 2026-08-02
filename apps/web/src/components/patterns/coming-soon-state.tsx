import { EmptyState, Clock } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type ComingSoonStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
  featureLabel?: string;
};

/**
 * Intentionally unfinished surface — honest, not a broken empty page.
 */
export function ComingSoonState({
  featureLabel = "This area",
  title,
  description,
  ...props
}: ComingSoonStateProps) {
  return (
    <EmptyState
      icon={Clock}
      title={title ?? `${featureLabel} is coming soon`}
      description={
        description ??
        "The shell and navigation are ready; product workflows for this section ship in a later phase. Check back after the next release."
      }
      {...props}
    />
  );
}
