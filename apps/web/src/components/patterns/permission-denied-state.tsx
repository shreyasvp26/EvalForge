import { EmptyState, Lock } from "@agent-eval/ui";

import type { EmptyStateProps } from "@agent-eval/ui";

export type PermissionDeniedStateProps = Omit<EmptyStateProps, "icon" | "title"> & {
  title?: string;
};

/**
 * Authorization failure — explain access, not a generic crash.
 */
export function PermissionDeniedState({
  title = "You don’t have access",
  description = "Your account isn’t permitted to view this resource. Ask a project admin to grant access, or switch to a project you can open.",
  ...props
}: PermissionDeniedStateProps) {
  return <EmptyState icon={Lock} title={title} description={description} {...props} />;
}
