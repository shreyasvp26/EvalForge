"use client";

import {
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Switch,
  Text,
  toast,
} from "@agent-eval/ui";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { usePreferences } from "./preferences-provider";
import { LANDING_PAGE_OPTIONS } from "./preferences-store";
import { SettingsShell } from "./settings-shell";

import { Section } from "@/components/layouts/section";

export function PreferencesSettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { preferences, hydrated, setDensity, setLandingPage, setReducedMotion } = usePreferences();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <SettingsShell
      title="Preferences"
      description="Browser-local UI preferences. Nothing here is synced to the Control Plane."
    >
      <Section title="Appearance" description="Theme via next-themes (system, light, or dark).">
        <div className="space-y-1.5">
          <Label>Theme</Label>
          <Select
            value={mounted ? (theme ?? "system") : "system"}
            onValueChange={(value) => {
              setTheme(value);
              toast.success("Theme updated");
            }}
          >
            <SelectTrigger className="max-w-xs">
              <SelectValue placeholder="Theme" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="system">System</SelectItem>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
            </SelectContent>
          </Select>
          {mounted ? <Text variant="caption">Resolved: {resolvedTheme ?? "—"}</Text> : null}
        </div>
      </Section>

      <Section title="Density" description="Comfortable for browsing; compact for dense tables.">
        <div className="space-y-1.5">
          <Label>Layout density</Label>
          <Select
            value={hydrated ? preferences.density : "comfortable"}
            onValueChange={(value) => {
              if (value === "comfortable" || value === "compact") {
                setDensity(value);
                toast.success("Density updated");
              }
            }}
          >
            <SelectTrigger className="max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="comfortable">Comfortable</SelectItem>
              <SelectItem value="compact">Compact</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Section>

      <Section
        title="Default landing page"
        description="Used after sign-in when no explicit redirect is provided."
      >
        <div className="space-y-1.5">
          <Label>Landing page</Label>
          <Select
            value={hydrated ? preferences.landingPage : "/"}
            onValueChange={(value) => {
              if (
                value === "/" ||
                value === "/projects" ||
                value === "/runs" ||
                value === "/agents"
              ) {
                setLandingPage(value);
                toast.success("Landing page updated");
              }
            }}
          >
            <SelectTrigger className="max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANDING_PAGE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Section>

      <Section title="Motion" description="Reduce transitions and decorative animation.">
        <label className="flex items-center justify-between gap-4 rounded-[var(--ef-radius-control)] border border-border px-3 py-2">
          <div className="space-y-0.5">
            <Text as="div" variant="body">
              Reduced motion
            </Text>
            <Text as="div" variant="caption">
              Prefer instant UI changes over animated transitions.
            </Text>
          </div>
          <Switch
            checked={hydrated ? preferences.reducedMotion : false}
            onCheckedChange={(checked) => {
              setReducedMotion(checked);
              toast.success(checked ? "Reduced motion on" : "Reduced motion off");
            }}
          />
        </label>
      </Section>
    </SettingsShell>
  );
}
