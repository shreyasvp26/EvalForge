"use client";

import { Button, CheckCircle2, FlaskConical, FolderKanban, Icon, Play, Text } from "@agent-eval/ui";
import Link from "next/link";

const STEPS = [
  {
    step: "01",
    title: "Create a project",
    body: "A project is the workspace for cases, suites, and runs.",
    href: "/projects?create=1",
    cta: "New project",
    icon: FolderKanban,
  },
  {
    step: "02",
    title: "Define a case",
    body: "Specify the prompt, repository context, and expected outcome.",
    href: "/cases",
    cta: "Browse cases",
    icon: FlaskConical,
  },
  {
    step: "03",
    title: "Choose agent & grader",
    body: "Pin an agent adapter and objective grader for reproducible scoring.",
    href: "/agents",
    cta: "Open agents",
    icon: CheckCircle2,
  },
  {
    step: "04",
    title: "Launch a run",
    body: "Execute, observe the timeline, and inspect scores and artifacts.",
    href: "/runs/new",
    cta: "Launch run",
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
          Build your first evaluation loop
        </Text>
        <Text as="p" variant="secondary" className="mt-2 max-w-2xl">
          EvalForge evaluates coding agents end-to-end. Follow this sequence once — then iterate on
          cases, agents, and graders.
        </Text>
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
