import { Cluster, Heading, Stack, Text, cn } from "@agent-eval/ui";

import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  /** Small mono/eyebrow label above the title (e.g. "Workspace"). */
  eyebrow?: ReactNode;
  /** Primary/secondary actions aligned to the right on desktop. */
  actions?: ReactNode;
  /** Optional breadcrumb row above the title block. */
  breadcrumbs?: ReactNode;
  className?: string;
}

/**
 * Page title region with optional eyebrow, description, and action cluster.
 */
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  breadcrumbs,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("space-y-4", className)}>
      {breadcrumbs ? <div className="min-w-0">{breadcrumbs}</div> : null}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <Stack gap={2} className="min-w-0 flex-1">
          {eyebrow ? (
            <Text variant="caption" className="font-mono uppercase tracking-wide">
              {eyebrow}
            </Text>
          ) : null}
          <Heading variant="page">{title}</Heading>
          {description ? (
            <Text variant="secondary" className="max-w-2xl">
              {description}
            </Text>
          ) : null}
        </Stack>
        {actions ? (
          <Cluster gap={2} className="shrink-0 sm:justify-end">
            {actions}
          </Cluster>
        ) : null}
      </div>
    </header>
  );
}
