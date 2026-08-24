"use client";

import { ArrowRight, Bot, FolderKanban, FlaskConical, Icon, Play, Text, cn } from "@agent-eval/ui";
import Link from "next/link";

import type { LucideIcon } from "@agent-eval/ui";

const ACTIONS: {
  href: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  primary?: boolean;
}[] = [
  {
    href: "/runs/new",
    label: "Launch evaluation",
    hint: "Pin case, agent, and grader versions",
    icon: Play,
    primary: true,
  },
  {
    href: "/projects?create=1",
    label: "Create project",
    hint: "New evaluation workspace",
    icon: FolderKanban,
  },
  {
    href: "/cases",
    label: "Define a case",
    hint: "Prompt and expected outcome",
    icon: FlaskConical,
  },
  {
    href: "/agents",
    label: "Configure agents",
    hint: "Adapters and versions",
    icon: Bot,
  },
];

export function QuickActions() {
  return (
    <ul className="space-y-2">
      {ACTIONS.map((action) => (
        <li key={action.href}>
          <Link
            href={action.href}
            className={cn(
              "group flex items-start gap-3 rounded-[var(--ef-radius-panel)] border px-3.5 py-3 transition-[background-color,border-color,box-shadow] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              action.primary
                ? "border-accent/30 bg-[var(--ef-accent-muted)]/40 hover:border-accent/50 hover:shadow-[0_0_0_1px_var(--ef-accent-glow)]"
                : "border-border bg-card hover:bg-muted/40",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
                action.primary
                  ? "bg-[var(--ef-accent-gradient)] text-[var(--ef-accent-foreground)]"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon icon={action.icon} size="sm" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <Text as="span" variant="body" className="font-medium">
                {action.label}
              </Text>
              <Text as="span" variant="caption" className="mt-0.5 block text-muted-foreground">
                {action.hint}
              </Text>
            </span>
            <Icon
              icon={ArrowRight}
              size="sm"
              className="mt-1 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 motion-reduce:opacity-100"
              aria-hidden
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}
