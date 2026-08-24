"use client";

import { Badge, Input, Label } from "@agent-eval/ui";

import { SettingsShell } from "./settings-shell";

import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { useAuth } from "@/lib/auth/auth-provider";

export function ProfileSettingsPage() {
  const { user, status } = useAuth();

  if (status === "restoring" || status === "restore_failed" || !user) {
    return (
      <SettingsShell title="Profile" description="Your Control Plane identity.">
        <DetailSkeleton withInspector={false} />
      </SettingsShell>
    );
  }

  return (
    <SettingsShell
      title="Profile"
      description="Identity from the authenticated session. Profile updates are not exposed by the API yet."
    >
      <Section title="Identity" description="Read-only while no profile update endpoint exists.">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="profile-display-name">Display name</Label>
            <Input id="profile-display-name" value={user.display_name} readOnly />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="profile-email">Email</Label>
            <Input id="profile-email" value={user.email} readOnly />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="profile-id">User ID</Label>
            <Input id="profile-id" value={user.id} readOnly className="font-mono" />
          </div>
          <Badge status="neutral">Read-only</Badge>
        </div>
      </Section>
    </SettingsShell>
  );
}
