"use client";

import { Text } from "@agent-eval/ui";

import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export function NavigationGallery() {
  return (
    <div className="space-y-4">
      <Text variant="secondary">
        Shell navigation is keyboard-first: ⌘K opens the command palette, G then P/R/A jumps to
        Projects / Runs / Agents, and ? opens the shortcut cheatsheet. Sidebar collapse and section
        open state persist in localStorage. Recent pages appear in the palette (client-only).
      </Text>
      <div className="rounded-[var(--ef-radius-panel)] border border-border bg-card p-4">
        <Text variant="table" className="mb-2">
          Breadcrumbs
        </Text>
        <Breadcrumbs
          items={[
            { label: "Workspace", href: "/" },
            { label: "Projects", href: "/" },
            { label: "Example" },
          ]}
        />
      </div>
      <ul className="list-disc space-y-2 pl-5 text-[length:var(--ef-text-body)] text-muted-foreground">
        <li>Desktop (lg+): collapsible persistent sidebar</li>
        <li>Below lg: overlay drawer with focus trap</li>
        <li>Command palette: fuzzy search, Recent / Navigate / Appearance / Help</li>
      </ul>
    </div>
  );
}
