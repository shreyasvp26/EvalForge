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

import { isNavActive, navSections } from "@/components/shell/nav-config";

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
        "group flex items-center gap-2 rounded-[var(--ef-radius-control)] text-[length:var(--ef-text-body)] transition-[background-color,color,padding] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        collapsed ? "justify-center px-2 py-2" : "px-2.5 py-1.5",
        active
          ? "bg-muted font-medium text-foreground shadow-[inset_2px_0_0_0_var(--ef-accent)]"
          : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
      )}
      {...(active ? { "aria-current": "page" as const } : {})}
    >
      <Icon icon={item.icon} size="sm" aria-hidden />
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
  return (
    <aside
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border bg-card transition-[width] duration-[var(--ef-duration-normal)] ease-[var(--ef-ease-standard)]",
        collapsed ? "w-[52px]" : "w-[15.5rem]",
        className,
      )}
      aria-label="Application"
    >
      <div
        className={cn(
          "flex h-12 items-center gap-2 border-b border-border",
          collapsed ? "justify-center px-1" : "px-3",
        )}
      >
        {!collapsed ? (
          <Link
            href="/"
            className="min-w-0 flex-1 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
          >
            <Text
              as="span"
              variant="caption"
              className="block truncate font-mono text-[length:var(--ef-text-body)] font-semibold uppercase tracking-[0.16em] text-foreground"
            >
              EvalForge
            </Text>
            <Text as="span" variant="caption" className="block truncate text-muted-foreground">
              Evaluation control plane
            </Text>
          </Link>
        ) : (
          <Link
            href="/"
            aria-label="EvalForge home"
            className="rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
          >
            <Text as="span" variant="caption" className="font-mono font-semibold text-foreground">
              EF
            </Text>
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

      <nav className="flex flex-1 flex-col gap-3 overflow-y-auto p-2" aria-label="Primary">
        {navSections.map((section) => {
          const open = sectionOpen[section.id] ?? true;
          return (
            <div key={section.id} className="space-y-0.5">
              {!collapsed ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-1 rounded-[var(--ef-radius-control)] px-2.5 py-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-expanded={open}
                  onClick={() => {
                    onToggleSection?.(section.id);
                  }}
                >
                  <Text
                    variant="caption"
                    className="flex-1 font-mono uppercase tracking-[0.12em] text-muted-foreground"
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
        <div className="space-y-1 border-t border-border p-3">
          <Text variant="caption" className="block text-muted-foreground">
            Press <kbd className="font-mono">?</kbd> for shortcuts
          </Text>
        </div>
      ) : null}
    </aside>
  );
}
