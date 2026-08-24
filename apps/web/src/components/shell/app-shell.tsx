"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useCallback, useState } from "react";

import type { ReactNode } from "react";

import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { MobileNavDrawer } from "@/components/shell/mobile-nav-drawer";
import { breadcrumbsForPath } from "@/components/shell/nav-config";
import { Sidebar } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";
import { useNavigationHotkeys } from "@/components/shell/use-navigation-hotkeys";
import { useRecentPages } from "@/components/shell/use-recent-pages";
import { useUiPreferences } from "@/components/shell/use-ui-preferences";

const CommandPalette = dynamic(
  () => import("@/components/shell/command-palette").then((mod) => mod.CommandPalette),
  { ssr: false },
);

const KeyboardShortcutsDialog = dynamic(
  () =>
    import("@/components/shell/keyboard-shortcuts-dialog").then(
      (mod) => mod.KeyboardShortcutsDialog,
    ),
  { ssr: false },
);

export function AppShell({
  children,
  breadcrumbs,
}: {
  children: ReactNode;
  breadcrumbs?: ReactNode;
}) {
  const pathname = usePathname();
  const { collapsed, setCollapsed, sectionOpen, toggleSection } = useUiPreferences();
  const { recent } = useRecentPages();
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  const openCommand = useCallback(() => {
    setCommandOpen(true);
  }, []);

  const openShortcuts = useCallback(() => {
    setShortcutsOpen(true);
  }, []);

  const closeOverlays = useCallback(() => {
    setCommandOpen(false);
    setMobileNavOpen(false);
    setShortcutsOpen(false);
  }, []);

  useNavigationHotkeys({
    onOpenCommand: openCommand,
    onOpenShortcuts: openShortcuts,
    onCloseOverlays: closeOverlays,
  });

  const autoBreadcrumbs = <Breadcrumbs items={breadcrumbsForPath(pathname)} />;

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--ef-surface-base)] text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-[var(--ef-z-toast)] focus:rounded-[var(--ef-radius-control)] focus:border focus:border-border focus:bg-card focus:px-3 focus:py-2 focus:text-[length:var(--ef-text-body)] focus:text-foreground focus:shadow-ef-md focus:outline-none focus:ring-2 focus:ring-ring"
      >
        Skip to content
      </a>
      <div className="hidden lg:flex">
        <Sidebar
          collapsed={collapsed}
          sectionOpen={sectionOpen}
          onToggleSection={toggleSection}
          onToggleCollapsed={() => {
            setCollapsed((value) => !value);
          }}
        />
      </div>

      <MobileNavDrawer
        open={mobileNavOpen}
        onOpenChange={setMobileNavOpen}
        sectionOpen={sectionOpen}
        onToggleSection={toggleSection}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          breadcrumbs={breadcrumbs ?? autoBreadcrumbs}
          onOpenCommand={openCommand}
          onOpenMobileNav={() => {
            setMobileNavOpen(true);
          }}
          onOpenShortcuts={openShortcuts}
        />
        <main id="main-content" className="min-h-0 flex-1 overflow-auto" tabIndex={-1}>
          {children}
        </main>
      </div>

      <CommandPalette
        open={commandOpen}
        onOpenChange={setCommandOpen}
        recent={recent}
        onOpenShortcuts={openShortcuts}
      />
      <KeyboardShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </div>
  );
}
