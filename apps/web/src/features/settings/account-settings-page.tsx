"use client";

import { Badge, Button, Text, toast } from "@agent-eval/ui";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { SettingsShell } from "./settings-shell";

import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { useAuth } from "@/lib/auth/auth-provider";
import { readTokenExpiresAt } from "@/lib/auth/session";

export function AccountSettingsPage() {
  const { user, status, logout } = useAuth();
  const router = useRouter();
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    setExpiresAt(readTokenExpiresAt());
  }, [status]);

  if (status === "loading" || !user) {
    return (
      <SettingsShell title="Account" description="Session and sign-out.">
        <DetailSkeleton withInspector={false} />
      </SettingsShell>
    );
  }

  const expiryLabel =
    expiresAt === null
      ? "Unknown"
      : expiresAt <= Date.now()
        ? "Expired"
        : new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          }).format(new Date(expiresAt));

  return (
    <SettingsShell
      title="Account"
      description="Session details for this browser. Credentials never leave the Control Plane auth flow."
    >
      <Section title="Session">
        <dl className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Status</Text>
            <Badge status="completed">Authenticated</Badge>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Signed in as</Text>
            <Text variant="body">{user.email}</Text>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Access token expires</Text>
            <Text variant="body" className="tabular-nums">
              {expiryLabel}
            </Text>
          </div>
        </dl>
      </Section>

      <Section title="Sign out" description="Clears the local JWT and session cookie.">
        <Button
          type="button"
          variant="danger"
          loading={signingOut}
          onClick={() => {
            setSigningOut(true);
            void (async () => {
              try {
                await logout();
                toast.success("Signed out");
                router.replace("/login");
              } finally {
                setSigningOut(false);
              }
            })();
          }}
        >
          Sign out
        </Button>
      </Section>
    </SettingsShell>
  );
}
