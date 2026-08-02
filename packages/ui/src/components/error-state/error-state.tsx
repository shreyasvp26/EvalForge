import { AlertCircle } from "../../icon/icons";
import { EmptyState } from "../empty-state/empty-state";

import type { EmptyStateProps } from "../empty-state/empty-state";

export type ErrorStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
};

export function ErrorState({
  title = "Something went wrong",
  description = "Try again, or check the logs for details.",
  ...props
}: ErrorStateProps) {
  return <EmptyState icon={AlertCircle} title={title} description={description} {...props} />;
}
