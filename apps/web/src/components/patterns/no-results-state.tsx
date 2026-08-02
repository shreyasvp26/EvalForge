import { EmptyState, Filter } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type NoResultsStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
};

/**
 * Filtered collection with zero rows — distinct from “never created anything”.
 */
export function NoResultsState({
  title = "No results with these filters",
  description = "Some filters may be excluding everything. Clear filters or broaden the criteria to see items again.",
  ...props
}: NoResultsStateProps) {
  return <EmptyState icon={Filter} title={title} description={description} {...props} />;
}
