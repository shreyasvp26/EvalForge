"use client";

import { Badge, Button, ExternalLink, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { SettingsShell } from "./settings-shell";

import { ErrorContent } from "@/components/layouts/error-content";
import { Section } from "@/components/layouts/section";
import { ApiError } from "@/lib/api/client";
import { getHealthLive, getHealthReady, getSystemInfo } from "@/lib/api/system";
import { useAuth } from "@/lib/auth/auth-provider";
import { buildInfo } from "@/lib/build-info";

export function AboutSettingsPage() {
  const { token } = useAuth();

  const systemQuery = useQuery({
    queryKey: ["system", "info"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getSystemInfo(token);
    },
  });

  const liveQuery = useQuery({
    queryKey: ["system", "health", "live"],
    queryFn: ({ signal }) => getHealthLive(signal),
    refetchInterval: 30_000,
  });

  const readyQuery = useQuery({
    queryKey: ["system", "health", "ready"],
    queryFn: ({ signal }) => getHealthReady(signal),
    refetchInterval: 30_000,
  });

  return (
    <SettingsShell title="About" description="Build metadata and Control Plane health.">
      <Section title="EvalForge web">
        <dl className="space-y-3">
          <MetaRow label="Version" value={buildInfo.version} />
          <MetaRow label="Git commit" value={buildInfo.gitCommit} mono />
          <MetaRow
            label="Build timestamp"
            value={buildInfo.buildTime ?? "Not set (local/dev build)"}
          />
          <MetaRow label="Environment" value={buildInfo.environment} />
        </dl>
        <Button asChild variant="outline" size="sm" className="mt-4" leftIcon={ExternalLink}>
          <a href={buildInfo.githubUrl} target="_blank" rel="noreferrer">
            Open GitHub repository
          </a>
        </Button>
      </Section>

      <Section title="Backend" description="From GET /v1/system/info (authenticated).">
        {systemQuery.isLoading ? (
          <Text variant="secondary">Loading system info…</Text>
        ) : systemQuery.isError ? (
          <ErrorContent
            title="Couldn’t load system info"
            description={
              systemQuery.error instanceof ApiError
                ? systemQuery.error.message
                : "Something went wrong."
            }
            action={
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => void systemQuery.refetch()}
              >
                Try again
              </Button>
            }
          />
        ) : systemQuery.data ? (
          <dl className="space-y-3">
            <MetaRow label="Service" value={systemQuery.data.service} />
            <MetaRow label="Version" value={systemQuery.data.version} />
            <MetaRow label="API version" value={systemQuery.data.api_version} />
            <MetaRow label="Environment" value={systemQuery.data.environment} />
          </dl>
        ) : null}
      </Section>

      <Section title="Health" description="Public liveness and readiness probes.">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Liveness (/health/live)</Text>
            <HealthBadge
              loading={liveQuery.isLoading}
              ok={liveQuery.data?.status === "ok"}
              error={liveQuery.isError}
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Text variant="caption">Readiness (/health/ready)</Text>
            <HealthBadge
              loading={readyQuery.isLoading}
              ok={readyQuery.data?.status === "ok"}
              error={readyQuery.isError}
            />
          </div>
          {readyQuery.data && Object.keys(readyQuery.data.checks).length > 0 ? (
            <ul className="divide-y divide-border rounded-[var(--ef-radius-control)] border border-border">
              {Object.entries(readyQuery.data.checks).map(([name, value]) => (
                <li key={name} className="flex items-center justify-between gap-2 px-3 py-2">
                  <Text variant="caption" className="font-mono">
                    {name}
                  </Text>
                  <Badge status={value === "ok" ? "completed" : "danger"}>{value}</Badge>
                </li>
              ))}
            </ul>
          ) : null}
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              void Promise.all([liveQuery.refetch(), readyQuery.refetch()]);
              toast.success("Health refreshed");
            }}
          >
            Refresh health
          </Button>
        </div>
      </Section>

      <Text variant="caption">
        Prefer the{" "}
        <Link href="/" className="text-accent underline-offset-2 hover:underline">
          Overview
        </Link>{" "}
        for product activity.
      </Text>
    </SettingsShell>
  );
}

function MetaRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <Text variant="caption">{label}</Text>
      <Text
        variant="body"
        className={mono ? "break-all font-mono text-[length:var(--ef-text-caption)]" : undefined}
      >
        {value}
      </Text>
    </div>
  );
}

function HealthBadge({ loading, ok, error }: { loading: boolean; ok: boolean; error: boolean }) {
  if (loading) return <Badge status="neutral">Checking…</Badge>;
  if (error) return <Badge status="danger">Unreachable</Badge>;
  if (ok) return <Badge status="completed">OK</Badge>;
  return <Badge status="warning">Not ready</Badge>;
}
