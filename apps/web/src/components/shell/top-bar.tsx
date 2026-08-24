"use client";

import { IconButton, Menu, Search, Text } from "@agent-eval/ui";

import type { ReactNode } from "react";

import { UserMenu } from "@/components/shell/user-menu";
import { ThemeToggle } from "@/components/theme-toggle";

export function TopBar({
  breadcrumbs,
  onOpenCommand,
  onOpenMobileNav,
  onOpenShortcuts,
}: {
  breadcrumbs?: ReactNode;
  onOpenCommand: () => void;
  onOpenMobileNav: () => void;
  onOpenShortcuts: () => void;
}) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-card/80 px-3 backdrop-blur-sm md:gap-3 md:px-4">
      <IconButton
        icon={Menu}
        label="Open navigation"
        className="lg:hidden"
        onClick={onOpenMobileNav}
      />
      <div className="min-w-0 flex-1">
        {breadcrumbs ?? (
          <Text variant="caption" className="font-mono uppercase tracking-[0.12em]">
            EvalForge
          </Text>
        )}
      </div>
      <IconButton
        icon={Search}
        label="Open command palette"
        className="sm:hidden"
        onClick={onOpenCommand}
      />
      <button
        type="button"
        onClick={onOpenCommand}
        className="hidden h-8 items-center gap-2 rounded-[var(--ef-radius-control)] border border-border bg-card px-2.5 text-muted-foreground transition-colors duration-[var(--ef-duration-fast)] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:inline-flex"
      >
        <Text as="span" variant="caption">
          Search
        </Text>
        <kbd className="rounded-[var(--ef-radius-control)] border border-border bg-muted px-1.5 font-mono text-[length:var(--ef-text-caption)] leading-none text-muted-foreground">
          ⌘K
        </kbd>
      </button>
      <button
        type="button"
        onClick={onOpenShortcuts}
        className="inline-flex h-8 min-w-8 items-center justify-center rounded-[var(--ef-radius-control)] border border-border px-2 font-mono text-[length:var(--ef-text-caption)] text-muted-foreground transition-colors duration-[var(--ef-duration-fast)] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Keyboard shortcuts"
      >
        ?
      </button>
      <ThemeToggle />
      <UserMenu />
    </header>
  );
}
