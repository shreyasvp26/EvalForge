"use client";

import { Button, FlaskConical, FolderKanban, GitBranch, Icon, Play, Text } from "@agent-eval/ui";
import Link from "next/link";

const STEPS = [
  {
    step: "01",
    title: "Create a project",
    body: "A project is the workspace for your engineering tasks and runs.",
    href: "/projects?create=1",
    cta: "New project",
    icon: FolderKanban,
  },
  {
    step: "02",
    title: "Connect GitHub",
    body: "Authorize EvalForge to read repositories and open reviewable PRs.",
    href: "/settings/github",
    cta: "Settings → GitHub",
    icon: GitBranch,
  },
  {
    step: "03",
    title: "Create a task",
    body: "Describe the work, pick a repository, and pin an exact commit SHA.",
    href: "/cases",
    cta: "Browse tasks",
    icon: FlaskConical,
  },
  {
    step: "04",
    title: "Run an agent",
    body: "Choose agent, model, and BYOK credential — then watch evaluation and PR outcome.",
    href: "/runs/new",
    cta: "New task run",
    icon: Play,
  },
] as const;

export function DashboardEmpty() {
  return (
    <div className="space-y-6">
      <div className="rounded-[var(--ef-radius-panel)] border border-border bg-card px-5 py-6 sm:px-6">
        <Text
          as="p"
          variant="caption"
          className="font-mono uppercase tracking-[0.14em] text-muted-foreground"
        >
          Getting started
        </Text>
        <Text
          as="div"
          variant="body"
          className="mt-2 text-[length:var(--ef-text-section)] font-medium"
        >
          Run an engineering task with a coding agent
        </Text>
        <Text as="p" variant="secondary" className="mt-2 max-w-2xl">
          Connect a GitHub repository, describe a real task, run an agent safely in Docker, grade
          the result, and get a reviewable PR when it passes — without automatic merges.
        </Text>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link href="/cases">New task</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link href="/settings/providers">Add BYOK credential</Link>
          </Button>
        </div>
      </div>

      <ol className="grid gap-3 sm:grid-cols-2">
        {STEPS.map((item) => (
          <li
            key={item.step}
            className="flex flex-col rounded-[var(--ef-radius-panel)] border border-border bg-card p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <Text as="span" variant="caption" className="font-mono text-muted-foreground">
                {item.step}
              </Text>
              <Icon icon={item.icon} size="sm" className="text-muted-foreground" aria-hidden />
            </div>
            <Text as="div" variant="body" className="mt-3 font-medium">
              {item.title}
            </Text>
            <Text as="p" variant="secondary" className="mt-1 flex-1">
              {item.body}
            </Text>
            <Button asChild variant="outline" size="sm" className="mt-4 self-start">
              <Link href={item.href}>{item.cta}</Link>
            </Button>
          </li>
        ))}
      </ol>
    </div>
  );
}
