"use client";

import { Badge, Button, Text, toast } from "@agent-eval/ui";
import { useEffect, useState } from "react";

import { SettingsShell } from "./settings-shell";

import { Section } from "@/components/layouts/section";
import { getApiBaseUrl } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";
import { readTokenExpiresAt } from "@/lib/auth/session";

function copyText(label: string, value: string) {
  void navigator.clipboard.writeText(value).then(
    () => {
      toast.success(`${label} copied`);
    },
    () => {
      toast.error(`Could not copy ${label.toLowerCase()}`);
    },
  );
}

export function ApiSettingsPage() {
  const { status, token } = useAuth();
  const [baseUrl, setBaseUrl] = useState("");
  const [expiresAt, setExpiresAt] = useState<number | null>(null);

  useEffect(() => {
    setBaseUrl(getApiBaseUrl());
    setExpiresAt(readTokenExpiresAt());
  }, [status, token]);

  const authLabel =
    status === "authenticated"
      ? "Authenticated"
      : status === "loading"
        ? "Checking…"
        : "Unauthenticated";

  const expiryLabel =
    expiresAt === null
      ? "—"
      : new Intl.DateTimeFormat(undefined, {
          dateStyle: "medium",
          timeStyle: "medium",
        }).format(new Date(expiresAt));

  return (
    <SettingsShell
      title="API"
      description="Control Plane connection details for this browser session."
    >
      <Section title="Endpoint">
        <dl className="space-y-4">
          <CopyRow
            label="API base URL"
            value={baseUrl || "—"}
            onCopy={() => {
              copyText("API base URL", baseUrl);
            }}
          />
          <CopyRow
            label="API version path"
            value="/v1"
            onCopy={() => {
              copyText("API version", "/v1");
            }}
          />
        </dl>
      </Section>

      <Section title="Authentication">
        <dl className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Status</Text>
            <Badge status={status === "authenticated" ? "completed" : "warning"}>{authLabel}</Badge>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">JWT expiry</Text>
            <Text variant="body" className="tabular-nums">
              {expiryLabel}
            </Text>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Token present</Text>
            <Text variant="body">{token ? "Yes" : "No"}</Text>
          </div>
        </dl>
        <Text variant="caption" className="mt-3 block">
          The access token is stored in localStorage for API calls. A presence cookie gates shell
          routes in middleware — it is not the credential.
        </Text>
      </Section>
    </SettingsShell>
  );
}

function CopyRow({ label, value, onCopy }: { label: string; value: string; onCopy: () => void }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <Text variant="caption">{label}</Text>
        <Button type="button" size="sm" variant="outline" onClick={onCopy}>
          Copy
        </Button>
      </div>
      <Text
        as="div"
        variant="body"
        className="break-all rounded-[var(--ef-radius-control)] border border-border bg-muted/40 px-3 py-2 font-mono text-[length:var(--ef-text-caption)]"
      >
        {value}
      </Text>
    </div>
  );
}
