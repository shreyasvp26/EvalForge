"use client";

import { Command, Icon, IconButton, Menu, Text } from "@agent-eval/ui";

import type { ReactNode } from "react";

import { ThemeToggle } from "@/components/theme-toggle";

export function TopBar({
  breadcrumbs,
  onOpenCommand,
  onOpenMobileNav,
}: {
  breadcrumbs?: ReactNode;
  onOpenCommand: () => void;
  onOpenMobileNav: () => void;
}) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-3 backdrop-blur-sm md:px-4">
      <IconButton
        icon={Menu}
        label="Open navigation"
        className="md:hidden"
        onClick={onOpenMobileNav}
      />
      <div className="min-w-0 flex-1">
        {breadcrumbs ?? <Text variant="caption">Workspace</Text>}
      </div>
      <button
        type="button"
        onClick={onOpenCommand}
        className="hidden h-8 items-center gap-2 rounded-[var(--ef-radius-control)] border border-border bg-card px-2.5 text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:inline-flex"
      >
        <Icon icon={Command} size="xs" aria-hidden />
        <Text as="span" variant="caption">
          Search
        </Text>
        <kbd className="rounded border border-border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </button>
      <ThemeToggle />
    </header>
  );
}
