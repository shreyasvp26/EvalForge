"use client";

import { Text, cn } from "@agent-eval/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface SettingsNavItem {
  href: string;
  label: string;
}

const SETTINGS_GROUPS: readonly {
  label: string;
  items: readonly SettingsNavItem[];
}[] = [
  {
    label: "Account",
    items: [
      { href: "/settings/profile", label: "Profile" },
      { href: "/settings/account", label: "Session" },
    ],
  },
  {
    label: "Providers",
    items: [
      { href: "/settings/providers", label: "Providers" },
      { href: "/settings/github", label: "GitHub" },
    ],
  },
  {
    label: "Preferences",
    items: [{ href: "/settings/preferences", label: "Preferences" }],
  },
  {
    label: "Diagnostics",
    items: [
      { href: "/settings/api", label: "API" },
      { href: "/settings/about", label: "About" },
    ],
  },
];

export const SETTINGS_NAV: SettingsNavItem[] = SETTINGS_GROUPS.flatMap((group) => [...group.items]);

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings" className="space-y-5">
      {SETTINGS_GROUPS.map((group) => (
        <div key={group.label} className="space-y-1">
          <Text
            as="div"
            variant="caption"
            className="px-3 font-medium uppercase tracking-wide text-muted-foreground"
          >
            {group.label}
          </Text>
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const active = pathname === item.href;
              return (
                <li key={item.href}>
                  <Link
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
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
