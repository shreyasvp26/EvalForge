import { EmptyState, SearchX } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type SearchEmptyStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
  query?: string;
};

/**
 * When a search query returns nothing — explain the query and next step.
 */
export function SearchEmptyState({ query, title, description, ...props }: SearchEmptyStateProps) {
  const resolvedTitle =
    title ?? (query !== undefined && query.length > 0 ? `No matches for “${query}”` : "No matches");
  const resolvedDescription =
    description ??
    "Try a different keyword, clear filters, or check spelling. Results update as you refine the query.";

  return (
    <EmptyState icon={SearchX} title={resolvedTitle} description={resolvedDescription} {...props} />
  );
}
