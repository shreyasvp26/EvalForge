"use client";

import { Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatCount } from "./utils";

import type { DashboardSummary } from "./utils";

export function PlatformSummary({ summary }: { summary: DashboardSummary }) {
  const items = [
    {
      label: "Projects",
      href: "/projects",
      value: formatCount(summary.projects, summary.projectsHasMore),
    },
    { label: "Suites", href: "/suites", value: String(summary.suites) },
    { label: "Tasks", href: "/cases", value: String(summary.cases) },
    {
      label: "Agents",
      href: "/agents",
      value: formatCount(summary.agents, summary.agentsHasMore),
    },
    {
      label: "Graders",
      href: "/graders",
      value: formatCount(summary.graders, summary.gradersHasMore),
    },
    { label: "Runs", href: "/runs", value: String(summary.runs) },
  ];

  return (
    <div className="flex flex-wrap items-baseline gap-x-1 gap-y-2 border-b border-border pb-4">
      {items.map((item, index) => (
        <div key={item.href} className="flex items-baseline gap-1">
          {index > 0 ? (
            <Text as="span" variant="caption" className="mx-2 text-border" aria-hidden>
              ·
            </Text>
          ) : null}
          <Link
            href={item.href}
            className="group inline-flex items-baseline gap-1.5 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Text
              as="span"
              variant="body"
              className="font-medium tabular-nums transition-colors group-hover:text-accent"
            >
              {item.value}
            </Text>
            <Text as="span" variant="caption">
              {item.label}
            </Text>
          </Link>
        </div>
      ))}
    </div>
  );
}
