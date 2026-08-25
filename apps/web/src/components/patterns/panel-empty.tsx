"use client";

import { Button, EmptyState, Play, cn } from "@agent-eval/ui";
import Link from "next/link";

import type { LucideIcon } from "@agent-eval/ui";
import type { ReactNode } from "react";

/**
 * Compact empty panel for dashboard / cockpit sections.
 * Teaches the next action without the full-page empty treatment.
 */
export function PanelEmpty({
  title,
  description,
  actionHref,
  actionLabel,
  icon,
  action,
  className,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  icon?: LucideIcon;
  action?: ReactNode;
  className?: string;
}) {
  const resolvedAction =
    action ??
    (actionHref && actionLabel ? (
      <Button asChild size="sm" variant="outline">
        <Link href={actionHref}>{actionLabel}</Link>
      </Button>
    ) : undefined);

  return (
    <EmptyState
      icon={icon ?? Play}
      title={title}
      description={description}
      action={resolvedAction}
      className={cn("gap-2 px-4 py-6", className)}
    />
  );
}
