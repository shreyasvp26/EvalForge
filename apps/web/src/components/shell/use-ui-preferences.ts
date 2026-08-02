"use client";

import { useCallback, useEffect, useState } from "react";

const SIDEBAR_COLLAPSED_KEY = "evalforge.sidebar.collapsed";
const SIDEBAR_SECTIONS_KEY = "evalforge.sidebar.sections";

export type SectionOpenState = Record<string, boolean>;

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function useUiPreferences() {
  const [collapsed, setCollapsedState] = useState(false);
  const [sectionOpen, setSectionOpenState] = useState<SectionOpenState>({
    workspace: true,
    system: true,
  });
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setCollapsedState(readJson(SIDEBAR_COLLAPSED_KEY, false));
    setSectionOpenState(readJson(SIDEBAR_SECTIONS_KEY, { workspace: true, system: true }));
    setHydrated(true);
  }, []);

  const setCollapsed = useCallback((value: boolean | ((prev: boolean) => boolean)) => {
    setCollapsedState((prev) => {
      const next = typeof value === "function" ? value(prev) : value;
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const setSectionOpen = useCallback(
    (value: SectionOpenState | ((prev: SectionOpenState) => SectionOpenState)) => {
      setSectionOpenState((prev) => {
        const next = typeof value === "function" ? value(prev) : value;
        window.localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify(next));
        return next;
      });
    },
    [],
  );

  const toggleSection = useCallback(
    (id: string) => {
      setSectionOpen((prev) => ({ ...prev, [id]: !(prev[id] ?? true) }));
    },
    [setSectionOpen],
  );

  return { collapsed, setCollapsed, sectionOpen, toggleSection, hydrated };
}
