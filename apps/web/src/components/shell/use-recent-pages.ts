"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { findNavItem } from "@/components/shell/nav-config";

const RECENT_KEY = "evalforge.nav.recent";
const MAX_RECENT = 8;

export interface RecentPage {
  href: string;
  label: string;
  visitedAt: number;
}

function readRecent(): RecentPage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (raw === null) return [];
    return JSON.parse(raw) as RecentPage[];
  } catch {
    return [];
  }
}

function writeRecent(items: RecentPage[]) {
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(items.slice(0, MAX_RECENT)));
}

export function useRecentPages() {
  const pathname = usePathname();
  const [recent, setRecent] = useState<RecentPage[]>([]);

  useEffect(() => {
    setRecent(readRecent());
  }, []);

  useEffect(() => {
    const item = findNavItem(pathname);
    if (!item) return;
    setRecent((prev) => {
      const next = [
        { href: item.href, label: item.label, visitedAt: Date.now() },
        ...prev.filter((entry) => entry.href !== item.href),
      ].slice(0, MAX_RECENT);
      writeRecent(next);
      return next;
    });
  }, [pathname]);

  const clearRecent = useCallback(() => {
    writeRecent([]);
    setRecent([]);
  }, []);

  return { recent, clearRecent };
}
