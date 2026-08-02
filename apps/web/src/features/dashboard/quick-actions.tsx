"use client";

import { Button, Text } from "@agent-eval/ui";
import Link from "next/link";

const ACTIONS = [
  { href: "/projects?create=1", label: "Create Project" },
  { href: "/runs/new", label: "Launch Run" },
  { href: "/agents", label: "Open Agents" },
  { href: "/graders", label: "Open Graders" },
] as const;

export function QuickActions() {
  return (
    <div className="space-y-3">
      <Text variant="caption">Jump into common workflows.</Text>
      <ul className="space-y-2">
        {ACTIONS.map((action) => (
          <li key={action.href}>
            <Button asChild variant="outline" size="sm" className="w-full justify-start">
              <Link href={action.href}>{action.label}</Link>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
