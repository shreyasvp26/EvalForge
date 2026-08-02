import { EmptyState, CheckCircle2 } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type SuccessStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
};

/**
 * Terminal success moment for wizards / completed flows (not toast-only).
 */
export function SuccessState({
  title = "Completed successfully",
  description = "You’re done here. Continue to the next step or return to the list when you’re ready.",
  ...props
}: SuccessStateProps) {
  return <EmptyState icon={CheckCircle2} title={title} description={description} {...props} />;
}
