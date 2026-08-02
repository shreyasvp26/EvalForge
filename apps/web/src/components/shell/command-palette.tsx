"use client";

import { BookOpen, Command as CommandIcon, Icon, Monitor, Moon, Sun, Text } from "@agent-eval/ui";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import type { RecentPage } from "@/components/shell/use-recent-pages";
import type { LucideIcon } from "@agent-eval/ui";

import { allNavItems } from "@/components/shell/nav-config";

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recent: RecentPage[];
  onOpenShortcuts: () => void;
}

function fuzzyScore(query: string, value: string): number {
  const q = query.trim().toLowerCase();
  if (q.length === 0) return 1;
  const v = value.toLowerCase();
  if (v.includes(q)) return 2;
  let qi = 0;
  for (let i = 0; i < v.length && qi < q.length; i += 1) {
    if (v[i] === q[qi]) qi += 1;
  }
  return qi === q.length ? 1 : 0;
}

export function CommandPalette({
  open,
  onOpenChange,
  recent,
  onOpenShortcuts,
}: CommandPaletteProps) {
  const router = useRouter();
  const { setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const run = useCallback(
    (href: string) => {
      onOpenChange(false);
      router.push(href);
    },
    [onOpenChange, router],
  );

  const navMatches = useMemo(() => {
    return allNavItems
      .map((item) => {
        const haystack = [item.label, item.href, ...(item.keywords ?? [])].join(" ");
        return { item, score: fuzzyScore(query, haystack) };
      })
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score);
  }, [query]);

  const recentMatches = useMemo(() => {
    return recent
      .map((page) => ({ page, score: fuzzyScore(query, `${page.label} ${page.href}`) }))
      .filter((entry) => entry.score > 0);
  }, [query, recent]);

  if (!mounted || !open) {
    return null;
  }

  const appearanceActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "theme-light",
      label: "Appearance: Light",
      icon: Sun,
      run: () => {
        setTheme("light");
        onOpenChange(false);
      },
    },
    {
      id: "theme-dark",
      label: "Appearance: Dark",
      icon: Moon,
      run: () => {
        setTheme("dark");
        onOpenChange(false);
      },
    },
    {
      id: "theme-system",
      label: "Appearance: System",
      icon: Monitor,
      run: () => {
        setTheme("system");
        onOpenChange(false);
      },
    },
  ];

  return createPortal(
    <div className="fixed inset-0 z-[var(--ef-z-command)]">
      <button
        type="button"
        className="absolute inset-0 bg-foreground/40"
        aria-label="Close command palette"
        onClick={() => {
          onOpenChange(false);
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative mx-auto mt-[12vh] w-[min(100%-1.5rem,560px)] overflow-hidden rounded-[var(--ef-radius-dialog)] border border-border bg-popover shadow-ef-md"
      >
        <Command
          label="Command palette"
          shouldFilter={false}
          className="flex flex-col"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onOpenChange(false);
            }
          }}
        >
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Icon icon={CommandIcon} size="sm" className="text-muted-foreground" aria-hidden />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Jump to a page, switch theme…"
              className="h-11 w-full bg-transparent text-[length:var(--ef-text-body)] text-popover-foreground outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-80 overflow-auto p-2">
            <Command.Empty className="px-2 py-6 text-center">
              <Text variant="secondary">No matching commands.</Text>
            </Command.Empty>

            {recentMatches.length > 0 ? (
              <Command.Group heading="Recent" className="mb-2">
                <Text variant="table" className="px-2 py-1.5">
                  Recent
                </Text>
                {recentMatches.map(({ page }) => {
                  const icon =
                    allNavItems.find((item) => item.href === page.href)?.icon ?? BookOpen;
                  return (
                    <Command.Item
                      key={`recent-${page.href}`}
                      value={`recent ${page.label} ${page.href}`}
                      onSelect={() => {
                        run(page.href);
                      }}
                      className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                    >
                      <Icon icon={icon} size="sm" aria-hidden />
                      <span className="flex-1 truncate">{page.label}</span>
                      <Text as="span" variant="caption">
                        Recent
                      </Text>
                    </Command.Item>
                  );
                })}
              </Command.Group>
            ) : null}

            {navMatches.length > 0 ? (
              <Command.Group heading="Navigate" className="mb-2">
                <Text variant="table" className="px-2 py-1.5">
                  Navigate
                </Text>
                {navMatches.map(({ item }) => (
                  <Command.Item
                    key={item.href}
                    value={`nav ${item.label} ${item.href} ${(item.keywords ?? []).join(" ")}`}
                    onSelect={() => {
                      run(item.href);
                    }}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                  >
                    <Icon icon={item.icon} size="sm" aria-hidden />
                    <span className="flex-1 truncate">{item.label}</span>
                    {item.chord ? (
                      <kbd className="font-mono text-[10px] text-muted-foreground">
                        {item.chord}
                      </kbd>
                    ) : null}
                  </Command.Item>
                ))}
              </Command.Group>
            ) : null}

            <Command.Group heading="Appearance" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Appearance
              </Text>
              {appearanceActions
                .filter((action) => fuzzyScore(query, action.label) > 0)
                .map((action) => (
                  <Command.Item
                    key={action.id}
                    value={action.label}
                    onSelect={() => {
                      action.run();
                    }}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                  >
                    <Icon icon={action.icon} size="sm" aria-hidden />
                    {action.label}
                  </Command.Item>
                ))}
            </Command.Group>

            <Command.Group heading="Help">
              <Text variant="table" className="px-2 py-1.5">
                Help
              </Text>
              {fuzzyScore(query, "keyboard shortcuts help") > 0 ? (
                <Command.Item
                  value="keyboard shortcuts help ?"
                  onSelect={() => {
                    onOpenChange(false);
                    onOpenShortcuts();
                  }}
                  className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                >
                  <Icon icon={CommandIcon} size="sm" aria-hidden />
                  Keyboard shortcuts
                  <kbd className="ml-auto font-mono text-[10px] text-muted-foreground">?</kbd>
                </Command.Item>
              ) : null}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>,
    document.body,
  );
}
