"use client";

import {
  ChevronDown,
  cn,
  Icon,
  IconButton,
  PanelLeft,
  Separator,
  SimpleTooltip,
  Text,
} from "@agent-eval/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { NavItem } from "@/components/shell/nav-config";
import type { SectionOpenState } from "@/components/shell/use-ui-preferences";

import { EvalForgeMark } from "@/components/brand/evalforge-mark";
import { isNavActive, navSections } from "@/components/shell/nav-config";
import { useAuth } from "@/lib/auth/auth-provider";

function initials(name: string, email: string): string {
  const source = name.trim() || email.trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]?.charAt(0) ?? ""}${parts[1]?.charAt(0) ?? ""}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase() || "?";
}

function NavLink({
  item,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = isNavActive(pathname, item.href);

  const link = (
    <Link
      href={item.href}
      {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
      {...(collapsed ? { "aria-label": item.label } : {})}
      title={collapsed ? item.label : undefined}
      className={cn(
        "group relative flex items-center gap-2.5 rounded-[var(--ef-radius-control)] text-[length:var(--ef-text-body)] transition-[background-color,color,box-shadow] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2.5",
        active
          ? "bg-[var(--ef-accent-muted)] font-medium text-foreground shadow-[inset_0_0_0_1px_var(--ef-auth-feature-border),0_0_20px_var(--ef-accent-glow)]"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
      {...(active ? { "aria-current": "page" as const } : {})}
    >
      {active ? (
        <span
          aria-hidden
          className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-[var(--ef-accent)]"
        />
      ) : null}
      <Icon
        icon={item.icon}
        size="sm"
        className={cn(active ? "text-[var(--ef-accent)]" : "text-current")}
        aria-hidden
      />
      {!collapsed ? (
        <>
          <span className="min-w-0 flex-1 truncate">{item.label}</span>
          {item.chord ? (
            <kbd className="hidden font-mono text-[length:var(--ef-text-caption)] leading-none text-muted-foreground opacity-0 transition-opacity motion-reduce:transition-none group-hover:opacity-100 xl:inline">
              {item.chord}
            </kbd>
          ) : null}
        </>
      ) : null}
    </Link>
  );

  if (collapsed) {
    return (
      <SimpleTooltip content={item.label}>
        <span className="block">{link}</span>
      </SimpleTooltip>
    );
  }

  return link;
}

export interface SidebarProps {
  className?: string;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  sectionOpen?: SectionOpenState;
  onToggleSection?: (id: string) => void;
  onNavigate?: () => void;
  showCollapseControl?: boolean;
}

export function Sidebar({
  className,
  collapsed = false,
  onToggleCollapsed,
  sectionOpen = { workspace: true, evaluation: true, system: true },
  onToggleSection,
  onNavigate,
  showCollapseControl = true,
}: SidebarProps) {
  const { user, status } = useAuth();

  return (
    <aside
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border bg-[var(--ef-surface-raised)] transition-[width] duration-[var(--ef-duration-normal)] ease-[var(--ef-ease-standard)]",
        collapsed ? "w-[56px]" : "w-[17rem]",
        className,
      )}
      aria-label="Application"
    >
      <div
        className={cn(
          "flex h-14 items-center gap-2 border-b border-border",
          collapsed ? "justify-center px-1" : "px-3.5",
        )}
      >
        {!collapsed ? (
          <Link
            href="/"
            className="flex min-w-0 flex-1 items-center gap-2.5 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
          >
            <EvalForgeMark size="sm" />
            <span className="min-w-0">
              <span className="block truncate font-mono text-[length:var(--ef-text-body)] font-semibold uppercase tracking-[0.16em] text-foreground">
                EvalForge
              </span>
            </span>
          </Link>
        ) : (
          <Link
            href="/"
            aria-label="EvalForge home"
            className="rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
          >
            <EvalForgeMark size="sm" />
          </Link>
        )}
        {showCollapseControl && onToggleCollapsed ? (
          <IconButton
            icon={PanelLeft}
            label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            size="sm"
            onClick={onToggleCollapsed}
            className={collapsed ? undefined : "ml-auto shrink-0"}
          />
        ) : null}
      </div>

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto p-2.5" aria-label="Primary">
        {navSections.map((section) => {
          const open = sectionOpen[section.id] ?? true;
          return (
            <div key={section.id} className="space-y-1">
              {!collapsed ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-1 rounded-[var(--ef-radius-control)] px-2.5 py-1.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-expanded={open}
                  onClick={() => {
                    onToggleSection?.(section.id);
                  }}
                >
                  <Text
                    variant="caption"
                    className="flex-1 font-mono uppercase tracking-[0.14em] text-muted-foreground"
                  >
                    {section.label}
                  </Text>
                  <Icon
                    icon={ChevronDown}
                    size="xs"
                    className={cn(
                      "text-muted-foreground transition-transform duration-[var(--ef-duration-fast)]",
                      open ? "rotate-0" : "-rotate-90",
                    )}
                    aria-hidden
                  />
                </button>
              ) : (
                <Separator className="my-1" />
              )}
              {collapsed || open
                ? section.items.map((item) => (
                    <NavLink
                      key={item.href}
                      item={item}
                      collapsed={collapsed}
                      {...(onNavigate !== undefined ? { onNavigate } : {})}
                    />
                  ))
                : null}
            </div>
          );
        })}
      </nav>

      {!collapsed ? (
        <div className="space-y-2 border-t border-border p-3">
          {status === "authenticated" && user ? (
            <div className="flex items-center gap-2.5 rounded-[var(--ef-radius-panel)] border border-border bg-muted/30 px-2.5 py-2">
              <span
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] bg-[var(--ef-accent-muted)] font-mono text-[length:var(--ef-text-caption)] font-semibold text-[var(--ef-accent)]"
                aria-hidden
              >
                {initials(user.display_name, user.email)}
              </span>
              <span className="min-w-0 flex-1">
                <Text
                  as="span"
                  variant="caption"
                  className="block truncate font-medium text-foreground"
                >
                  {user.display_name || "Account"}
                </Text>
                <Text as="span" variant="caption" className="block truncate text-muted-foreground">
                  {user.email}
                </Text>
              </span>
            </div>
          ) : null}
          <Text variant="caption" className="block px-0.5 text-muted-foreground">
            Press <kbd className="font-mono">?</kbd> for shortcuts
          </Text>
        </div>
      ) : null}
    </aside>
  );
}
