"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";

import type { ReactNode } from "react";

import { Sidebar } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";

const CommandPalette = dynamic(
  () => import("@/components/shell/command-palette").then((mod) => mod.CommandPalette),
  { ssr: false },
);

export function AppShell({
  children,
  breadcrumbs,
}: {
  children: ReactNode;
  breadcrumbs?: ReactNode;
}) {
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const onKeyDown = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      setCommandOpen((open) => !open);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onKeyDown]);

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      {mobileNavOpen ? (
        <div className="fixed inset-0 z-[var(--ef-z-overlay)] md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-foreground/40"
            aria-label="Close navigation"
            onClick={() => {
              setMobileNavOpen(false);
            }}
          />
          <div className="relative h-full w-60 shadow-ef-md">
            <Sidebar
              onNavigate={() => {
                setMobileNavOpen(false);
              }}
            />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          {...(breadcrumbs !== undefined ? { breadcrumbs } : {})}
          onOpenCommand={() => {
            setCommandOpen(true);
          }}
          onOpenMobileNav={() => {
            setMobileNavOpen(true);
          }}
        />
        <main className="min-h-0 flex-1 overflow-auto">{children}</main>
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
