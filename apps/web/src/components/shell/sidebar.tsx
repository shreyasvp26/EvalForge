"use client";

import {
  BookOpen,
  cn,
  FlaskConical,
  FolderKanban,
  Icon,
  Layers,
  Play,
  Separator,
  Text,
} from "@agent-eval/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { LucideIcon } from "@agent-eval/ui";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const primaryNav: NavItem[] = [
  { href: "/", label: "Projects", icon: FolderKanban },
  { href: "/suites", label: "Suites", icon: Layers },
  { href: "/cases", label: "Cases", icon: FlaskConical },
  { href: "/runs", label: "Runs", icon: Play },
];

const secondaryNav: NavItem[] = [
  { href: "/design-system", label: "Design system", icon: BookOpen },
];

function NavLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const pathname = usePathname();
  const active =
    item.href === "/"
      ? pathname === "/"
      : pathname === item.href || pathname.startsWith(`${item.href}/`);

  return (
    <Link
      href={item.href}
      {...(onNavigate !== undefined ? { onClick: onNavigate } : {})}
      className={cn(
        "flex items-center gap-2 rounded-[var(--ef-radius-control)] px-2.5 py-2 text-[length:var(--ef-text-body)] transition-colors duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "bg-muted font-medium text-foreground"
          : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
      )}
      {...(active ? { "aria-current": "page" as const } : {})}
    >
      <Icon icon={item.icon} size="sm" aria-hidden />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function Sidebar({
  className,
  onNavigate,
}: {
  className?: string;
  onNavigate?: () => void;
}) {
  return (
    <aside
      className={cn("flex h-full w-60 shrink-0 flex-col border-r border-border bg-card", className)}
    >
      <div className="flex h-12 items-center gap-2 px-4">
        <Text
          as="span"
          variant="caption"
          className="font-mono uppercase tracking-[0.14em] text-foreground"
        >
          EvalForge
        </Text>
      </div>
      <Separator />
      <nav className="flex flex-1 flex-col gap-6 p-3" aria-label="Primary">
        <div className="space-y-1">
          <Text variant="table" className="px-2.5 pb-1">
            Workspace
          </Text>
          {primaryNav.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              {...(onNavigate !== undefined ? { onNavigate } : {})}
            />
          ))}
        </div>
        <div className="space-y-1">
          <Text variant="table" className="px-2.5 pb-1">
            System
          </Text>
          {secondaryNav.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              {...(onNavigate !== undefined ? { onNavigate } : {})}
            />
          ))}
        </div>
      </nav>
      <div className="border-t border-border p-3">
        <Text variant="caption">Projects → Suites → Cases → Runs</Text>
      </div>
    </aside>
  );
}
