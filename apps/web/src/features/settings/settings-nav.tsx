"use client";

import { Text, cn } from "@agent-eval/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";

export const SETTINGS_NAV = [
  { href: "/settings/profile", label: "Profile" },
  { href: "/settings/account", label: "Account" },
  { href: "/settings/preferences", label: "Preferences" },
  { href: "/settings/api", label: "API" },
  { href: "/settings/about", label: "About" },
] as const;

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings" className="space-y-1">
      {SETTINGS_NAV.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "block rounded-[var(--ef-radius-control)] px-3 py-1.5 text-[length:var(--ef-text-body)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active
                ? "bg-muted font-medium text-foreground"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
      <Text as="p" variant="caption" className="px-3 pt-3">
        Settings stay quiet and local where possible.
      </Text>
    </nav>
  );
}
