export type DensityPreference = "comfortable" | "compact";
export type LandingPagePreference = "/" | "/projects" | "/runs" | "/agents";

export interface UserPreferences {
  density: DensityPreference;
  landingPage: LandingPagePreference;
  reducedMotion: boolean;
}

export const USER_PREFERENCES_KEY = "evalforge.preferences";

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  density: "comfortable",
  landingPage: "/",
  reducedMotion: false,
};

export const LANDING_PAGE_OPTIONS: {
  value: LandingPagePreference;
  label: string;
}[] = [
  { value: "/", label: "Overview" },
  { value: "/projects", label: "Projects" },
  { value: "/runs", label: "Runs" },
  { value: "/agents", label: "Agents" },
];

function isLandingPage(value: unknown): value is LandingPagePreference {
  return value === "/" || value === "/projects" || value === "/runs" || value === "/agents";
}

export function readUserPreferences(): UserPreferences {
  if (typeof window === "undefined") return DEFAULT_USER_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(USER_PREFERENCES_KEY);
    if (!raw) return DEFAULT_USER_PREFERENCES;
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    return {
      density: parsed.density === "compact" ? "compact" : "comfortable",
      landingPage: isLandingPage(parsed.landingPage)
        ? parsed.landingPage
        : DEFAULT_USER_PREFERENCES.landingPage,
      reducedMotion: Boolean(parsed.reducedMotion),
    };
  } catch {
    return DEFAULT_USER_PREFERENCES;
  }
}

export function writeUserPreferences(prefs: UserPreferences): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_PREFERENCES_KEY, JSON.stringify(prefs));
}

export function applyUserPreferences(prefs: UserPreferences): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset["density"] = prefs.density;
  root.dataset["reducedMotion"] = prefs.reducedMotion ? "true" : "false";
}
