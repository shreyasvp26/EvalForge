import { EmptyState, FileText } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type NotFoundStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
  resourceLabel?: string;
};

/**
 * Missing resource (bad URL, deleted entity). Offer a path back to a safe list.
 */
export function NotFoundState({
  resourceLabel = "page",
  title,
  description,
  ...props
}: NotFoundStateProps) {
  return (
    <EmptyState
      icon={FileText}
      title={title ?? `This ${resourceLabel} could not be found`}
      description={
        description ??
        "It may have been deleted, moved, or you may not have the correct link. Return to the list and open an item from there."
      }
      {...props}
    />
  );
}
