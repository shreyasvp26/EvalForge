"use client";

import { Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatDashboardDate } from "./utils";

export interface ResourceRow {
  id: string;
  title: string;
  meta?: string;
  href: string;
  timestamp: string;
}

export function ResourceList({ rows, emptyLabel }: { rows: ResourceRow[]; emptyLabel: string }) {
  if (rows.length === 0) {
    return <Text variant="secondary">{emptyLabel}</Text>;
  }

  return (
    <ul className="divide-y divide-border border-y border-border">
      {rows.map((row) => (
        <li key={row.id}>
          <Link
            href={row.href}
            className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-2.5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Text as="span" variant="body" className="min-w-0 truncate font-medium">
              {row.title}
            </Text>
            {row.meta ? (
              <Text as="span" variant="caption" className="min-w-0 truncate">
                {row.meta}
              </Text>
            ) : null}
            <Text as="span" variant="caption" className="ml-auto shrink-0 tabular-nums">
              {formatDashboardDate(row.timestamp)}
            </Text>
          </Link>
        </li>
      ))}
    </ul>
  );
}
