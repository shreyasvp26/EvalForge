"use client";

import { Button, Text } from "@agent-eval/ui";
import Link from "next/link";

const ACTIONS: {
  href: string;
  label: string;
  hint: string;
  primary?: boolean;
}[] = [
  {
    href: "/runs/new",
    label: "Launch evaluation",
    hint: "Pin case, agent, and grader versions",
    primary: true,
  },
  {
    href: "/projects?create=1",
    label: "Create project",
    hint: "New evaluation workspace",
  },
  {
    href: "/cases",
    label: "Define a case",
    hint: "Prompt and expected outcome",
  },
  {
    href: "/agents",
    label: "Configure agents",
    hint: "Adapters and versions",
  },
];

export function QuickActions() {
  return (
    <ul className="space-y-2">
      {ACTIONS.map((action) => (
        <li key={action.href}>
          <Button
            asChild
            variant={action.primary ? "primary" : "outline"}
            size="sm"
            className="h-auto w-full justify-start px-3 py-2.5"
          >
            <Link href={action.href} className="flex flex-col items-start gap-0.5 text-left">
              <span>{action.label}</span>
              <Text as="span" variant="caption" className="font-normal opacity-80">
                {action.hint}
              </Text>
            </Link>
          </Button>
        </li>
      ))}
    </ul>
  );
}
