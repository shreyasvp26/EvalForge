"use client";

import { useCallback, useEffect, useState } from "react";

const SIDEBAR_COLLAPSED_KEY = "evalforge.sidebar.collapsed";
const SIDEBAR_SECTIONS_KEY = "evalforge.sidebar.sections";

export type SectionOpenState = Record<string, boolean>;

const DEFAULT_SECTIONS: SectionOpenState = {
  workspace: true,
  evaluation: true,
  system: true,
};

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
  const [sectionOpen, setSectionOpenState] = useState<SectionOpenState>(DEFAULT_SECTIONS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setCollapsedState(readJson(SIDEBAR_COLLAPSED_KEY, false));
    const stored = readJson<SectionOpenState>(SIDEBAR_SECTIONS_KEY, DEFAULT_SECTIONS);
    setSectionOpenState({ ...DEFAULT_SECTIONS, ...stored });
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
