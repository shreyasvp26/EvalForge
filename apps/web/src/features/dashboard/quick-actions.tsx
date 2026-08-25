"use client";

import {
  ArrowRight,
  BarChart3,
  Bot,
  FolderKanban,
  FlaskConical,
  Icon,
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
    hint: "Start a new evaluation workspace",
    icon: FolderKanban,
    tone: "blue",
  },
  {
    href: "/cases",
    label: "Create case",
    hint: "Define a prompt and expected outcome",
    icon: FlaskConical,
    tone: "violet",
  },
  {
    href: "/agents",
    label: "Configure agents",
    hint: "Adapters, models, and versions",
    icon: Bot,
    tone: "emerald",
  },
  {
    href: "/graders",
    label: "Configure graders",
    hint: "Scoring rules and thresholds",
    icon: BarChart3,
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
    <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {ACTIONS.map((action) => (
        <li key={action.href}>
          <Link
            href={action.href}
            className={cn(
              "group flex h-full items-start gap-3 rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm transition-[border-color,box-shadow,transform] duration-[var(--ef-duration-fast)] hover:-translate-y-0.5 hover:border-[var(--ef-auth-feature-border)] hover:shadow-[0_8px_28px_var(--ef-accent-glow)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:hover:translate-y-0",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
                toneClass[action.tone],
              )}
            >
              <Icon icon={action.icon} size="sm" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <Text as="span" variant="body" className="block font-medium text-foreground">
                {action.label}
              </Text>
              <Text as="span" variant="caption" className="mt-1 block text-muted-foreground">
                {action.hint}
              </Text>
            </span>
            <Icon
              icon={ArrowRight}
              size="sm"
              className="mt-1 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 motion-reduce:opacity-60"
              aria-hidden
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}
