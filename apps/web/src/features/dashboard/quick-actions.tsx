"use client";

import {
  ArrowRight,
  FolderKanban,
  FlaskConical,
  GitBranch,
  Icon,
  Lock,
  Text,
  cn,
} from "@agent-eval/ui";
import Link from "next/link";

import type { LucideIcon } from "@agent-eval/ui";

const ACTIONS: {
  href: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  tone: "blue" | "violet" | "amber" | "emerald";
}[] = [
  {
    href: "/projects?create=1",
    label: "Create project",
    hint: "Workspace for tasks and runs",
    icon: FolderKanban,
    tone: "blue",
  },
  {
    href: "/cases",
    label: "New task",
    hint: "Describe work against a GitHub revision",
    icon: FlaskConical,
    tone: "violet",
  },
  {
    href: "/settings/github",
    label: "Connect GitHub",
    hint: "Authorize repo access and publication",
    icon: GitBranch,
    tone: "emerald",
  },
  {
    href: "/settings/providers",
    label: "Add BYOK credential",
    hint: "Provider keys for coding agents",
    icon: Lock,
    tone: "amber",
  },
];

const toneClass: Record<(typeof ACTIONS)[number]["tone"], string> = {
  blue: "bg-running-muted text-running",
  violet: "bg-[var(--ef-accent-muted)] text-[var(--ef-accent)]",
  emerald: "bg-success-muted text-success",
  amber: "bg-warning-muted text-warning",
};

export function QuickActions() {
  return (
    <ul className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
      {ACTIONS.map((action) => (
        <li key={action.href}>
          <Link
            href={action.href}
            className={cn(
              "group flex h-full items-start gap-2.5 rounded-[var(--ef-radius-panel)] border border-border bg-card px-3 py-2.5 transition-[border-color,background-color,box-shadow] duration-[var(--ef-duration-fast)] hover:border-border-strong hover:bg-muted/25 hover:shadow-ef-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
                toneClass[action.tone],
              )}
            >
              <Icon icon={action.icon} size="sm" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <Text as="span" variant="body" className="block font-medium text-foreground">
                {action.label}
              </Text>
              <Text as="span" variant="caption" className="mt-0.5 block text-muted-foreground">
                {action.hint}
              </Text>
            </span>
            <Icon
              icon={ArrowRight}
              size="sm"
              className="mt-0.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 motion-reduce:opacity-60"
              aria-hidden
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}
