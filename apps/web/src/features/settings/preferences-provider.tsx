"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  DEFAULT_USER_PREFERENCES,
  applyUserPreferences,
  readUserPreferences,
  writeUserPreferences,
} from "./preferences-store";

import type {
  DensityPreference,
  LandingPagePreference,
  UserPreferences,
} from "./preferences-store";
import type { ReactNode } from "react";

interface PreferencesContextValue {
  preferences: UserPreferences;
  hydrated: boolean;
  setDensity: (density: DensityPreference) => void;
  setLandingPage: (landingPage: LandingPagePreference) => void;
  setReducedMotion: (reducedMotion: boolean) => void;
  updatePreferences: (patch: Partial<UserPreferences>) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_USER_PREFERENCES);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const next = readUserPreferences();
    setPreferences(next);
    applyUserPreferences(next);
    setHydrated(true);
  }, []);

  const commit = useCallback((next: UserPreferences) => {
    setPreferences(next);
    writeUserPreferences(next);
    applyUserPreferences(next);
  }, []);

  const updatePreferences = useCallback(
    (patch: Partial<UserPreferences>) => {
      commit({ ...preferences, ...patch });
    },
    [commit, preferences],
  );

  const setDensity = useCallback(
    (density: DensityPreference) => {
      updatePreferences({ density });
    },
    [updatePreferences],
  );

  const setLandingPage = useCallback(
    (landingPage: LandingPagePreference) => {
      updatePreferences({ landingPage });
    },
    [updatePreferences],
  );

  const setReducedMotion = useCallback(
    (reducedMotion: boolean) => {
      updatePreferences({ reducedMotion });
    },
    [updatePreferences],
  );

  const value = useMemo(
    () => ({
      preferences,
      hydrated,
      setDensity,
      setLandingPage,
      setReducedMotion,
      updatePreferences,
    }),
    [preferences, hydrated, setDensity, setLandingPage, setReducedMotion, updatePreferences],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (!value) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return value;
}
