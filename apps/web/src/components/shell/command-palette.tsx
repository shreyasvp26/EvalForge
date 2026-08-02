"use client";

import {
  BookOpen,
  Command as CommandIcon,
  FlaskConical,
  FolderKanban,
  Icon,
  Layers,
  Play,
  Text,
} from "@agent-eval/ui";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const items = [
  { href: "/", label: "Projects", icon: FolderKanban, group: "Navigate" },
  { href: "/suites", label: "Suites", icon: Layers, group: "Navigate" },
  { href: "/cases", label: "Cases", icon: FlaskConical, group: "Navigate" },
  { href: "/runs", label: "Runs", icon: Play, group: "Navigate" },
  { href: "/design-system", label: "Design system", icon: BookOpen, group: "System" },
] as const;

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const run = useCallback(
    (href: string) => {
      onOpenChange(false);
      router.push(href);
    },
    [onOpenChange, router],
  );

  if (!mounted || !open) {
    return null;
  }

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
      <div className="relative mx-auto mt-[15vh] w-[min(100%-1.5rem,560px)] overflow-hidden rounded-[var(--ef-radius-dialog)] border border-border bg-popover shadow-ef-md">
        <Command
          label="Command palette"
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
              placeholder="Jump to…"
              className="h-11 w-full bg-transparent text-[length:var(--ef-text-body)] text-popover-foreground outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-80 overflow-auto p-2">
            <Command.Empty className="px-2 py-6 text-center">
              <Text variant="secondary">No matching destinations.</Text>
            </Command.Empty>
            {(["Navigate", "System"] as const).map((group) => (
              <Command.Group key={group} heading={group} className="mb-2">
                <Text variant="table" className="px-2 py-1.5">
                  {group}
                </Text>
                {items
                  .filter((item) => item.group === group)
                  .map((item) => (
                    <Command.Item
                      key={item.href}
                      value={`${item.label} ${item.href}`}
                      onSelect={() => {
                        run(item.href);
                      }}
                      className="flex cursor-pointer items-center gap-2 rounded-[var(--ef-radius-control)] px-2 py-2 text-[length:var(--ef-text-body)] text-popover-foreground aria-selected:bg-muted"
                    >
                      <Icon icon={item.icon} size="sm" aria-hidden />
                      {item.label}
                    </Command.Item>
                  ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>,
    document.body,
  );
}
