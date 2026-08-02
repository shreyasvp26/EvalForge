"use client";

import {
  BookOpen,
  Bot,
  CheckCircle2,
  Command as CommandIcon,
  Dialog,
  DialogContent,
  DialogTitleHidden,
  FlaskConical,
  FolderKanban,
  Icon,
  Layers,
  LogOut,
  Monitor,
  Moon,
  Play,
  Plus,
  Sun,
  Text,
} from "@agent-eval/ui";
import { Command } from "cmdk";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { RecentPage } from "@/components/shell/use-recent-pages";
import type { LucideIcon } from "@agent-eval/ui";

import { allNavItems } from "@/components/shell/nav-config";
import { useAuth } from "@/lib/auth/auth-provider";

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
  const pathname = usePathname();
  const { setTheme } = useTheme();
  const { logout } = useAuth();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const projectIdFromPath = useMemo(() => {
    const match = /^\/projects\/([^/]+)/.exec(pathname);
    return match?.[1] ?? null;
  }, [pathname]);

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

  const projectActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-projects",
      label: "Open Projects",
      icon: FolderKanban,
      run: () => {
        run("/projects");
      },
    },
    {
      id: "create-project",
      label: "Create Project",
      icon: Plus,
      run: () => {
        run("/projects?create=1");
      },
    },
  ];

  const suiteActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-suites",
      label: "Open Suites",
      icon: Layers,
      run: () => {
        if (projectIdFromPath) {
          run(`/projects/${projectIdFromPath}/suites`);
        } else {
          run("/suites");
        }
      },
    },
    {
      id: "create-suite",
      label: "Create Suite",
      icon: Plus,
      run: () => {
        if (projectIdFromPath) {
          run(`/projects/${projectIdFromPath}/suites?create=1`);
        } else {
          run("/suites");
        }
      },
    },
  ];

  const caseActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-cases",
      label: "Open Cases",
      icon: FlaskConical,
      run: () => {
        if (projectIdFromPath) {
          run(`/projects/${projectIdFromPath}/cases`);
        } else {
          run("/cases");
        }
      },
    },
    {
      id: "create-case",
      label: "Create Case",
      icon: Plus,
      run: () => {
        if (projectIdFromPath) {
          run(`/projects/${projectIdFromPath}/cases?create=1`);
        } else {
          run("/cases");
        }
      },
    },
  ];

  const runActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-runs",
      label: "Open Runs",
      icon: Play,
      run: () => {
        run("/runs");
      },
    },
    {
      id: "create-run",
      label: "New Run",
      icon: Plus,
      run: () => {
        run("/runs/new");
      },
    },
  ];

  const agentActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-agents",
      label: "Open Agents",
      icon: Bot,
      run: () => {
        run("/agents");
      },
    },
    {
      id: "create-agent",
      label: "Create Agent",
      icon: Plus,
      run: () => {
        run("/agents?create=1");
      },
    },
  ];

  const graderActions: { id: string; label: string; icon: LucideIcon; run: () => void }[] = [
    {
      id: "open-graders",
      label: "Open Graders",
      icon: CheckCircle2,
      run: () => {
        run("/graders");
      },
    },
    {
      id: "create-grader",
      label: "Create Grader",
      icon: Plus,
      run: () => {
        run("/graders?create=1");
      },
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showClose={false}
        aria-describedby={undefined}
        overlayClassName="z-[var(--ef-z-command)]"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          inputRef.current?.focus();
        }}
        className="fixed left-1/2 top-[12vh] z-[var(--ef-z-command)] grid w-[min(100%-1.5rem,560px)] max-w-[560px] -translate-x-1/2 translate-y-0 gap-0 overflow-hidden rounded-[var(--ef-radius-dialog)] border border-border bg-popover p-0 text-popover-foreground shadow-ef-md"
      >
        <DialogTitleHidden>Command palette</DialogTitleHidden>
        <Command
          label="Command palette"
          shouldFilter={false}
          className="flex flex-col"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              onOpenChange(false);
            }
          }}
        >
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Icon icon={CommandIcon} size="sm" className="text-muted-foreground" aria-hidden />
            <Command.Input
              ref={inputRef}
              value={query}
              onValueChange={setQuery}
              placeholder="Jump to a page, switch theme…"
              className="h-11 w-full bg-transparent text-[length:var(--ef-text-body)] text-popover-foreground outline-none placeholder:text-muted-foreground focus-visible:outline-none"
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
                      <kbd className="font-mono text-[length:var(--ef-text-caption)] leading-none text-muted-foreground">
                        {item.chord}
                      </kbd>
                    ) : null}
                  </Command.Item>
                ))}
              </Command.Group>
            ) : null}

            <Command.Group heading="Projects" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Projects
              </Text>
              {projectActions
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

            <Command.Group heading="Suites" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Suites
              </Text>
              {suiteActions
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

            <Command.Group heading="Cases" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Cases
              </Text>
              {caseActions
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

            <Command.Group heading="Runs" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Runs
              </Text>
              {runActions
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

            <Command.Group heading="Agents" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Agents
              </Text>
              {agentActions
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

            <Command.Group heading="Graders" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Graders
              </Text>
              {graderActions
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

            <Command.Group heading="Account" className="mb-2">
              <Text variant="table" className="px-2 py-1.5">
                Account
              </Text>
              {fuzzyScore(query, "sign out logout account") > 0 ? (
                <Command.Item
                  value="sign out logout account"
                  onSelect={() => {
                    onOpenChange(false);
                    void (async () => {
                      await logout();
                      router.replace("/login");
                    })();
                  }}
                  className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                >
                  <Icon icon={LogOut} size="sm" aria-hidden />
                  Sign out
                </Command.Item>
              ) : null}
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
                  <kbd className="ml-auto font-mono text-[length:var(--ef-text-caption)] leading-none text-muted-foreground">
                    ?
                  </kbd>
                </Command.Item>
              ) : null}
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
