"use client";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
  LogOut,
  Text,
  User,
} from "@agent-eval/ui";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth/auth-provider";

function initials(name: string, email: string): string {
  const source = name.trim() || email.trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    const first = parts[0]?.charAt(0) ?? "";
    const second = parts[1]?.charAt(0) ?? "";
    return `${first}${second}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase() || "?";
}

export function UserMenu() {
  const { user, logout, status } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  if (status !== "authenticated" || !user) {
    return null;
  }

  async function onSignOut() {
    setSigningOut(true);
    try {
      await logout();
      router.replace("/login");
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex h-8 max-w-[12rem] items-center gap-2 rounded-[var(--ef-radius-control)] border border-border bg-card px-2 text-foreground transition-colors duration-[var(--ef-duration-fast)] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Account menu"
        >
          <span
            className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] bg-muted font-mono text-[10px] font-medium text-muted-foreground"
            aria-hidden
          >
            {initials(user.display_name, user.email)}
          </span>
          <Text as="span" variant="caption" className="truncate">
            {user.display_name || user.email}
          </Text>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="space-y-0.5 font-normal">
          <Text as="div" variant="body" className="truncate font-medium text-foreground">
            {user.display_name}
          </Text>
          <Text as="div" variant="caption" className="truncate">
            {user.email}
          </Text>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled className="gap-2 opacity-70">
          <Icon icon={User} size="sm" aria-hidden />
          Account
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={signingOut}
          className="gap-2"
          onSelect={(event) => {
            event.preventDefault();
            void onSignOut();
          }}
        >
          <Icon icon={LogOut} size="sm" aria-hidden />
          {signingOut ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
