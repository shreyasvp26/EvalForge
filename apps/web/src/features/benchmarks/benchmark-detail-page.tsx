"use client";

import {
  Badge,
  Button,
  Cluster,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Text,
  toast,
} from "@agent-eval/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { InlineError } from "@/components/patterns/inline-error";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { adapterQueryKey, agentsQueryKey } from "@/features/agents/utils";
import { isPinnableVersionStatus } from "@/features/cases/utils";
import { projectQueryKey } from "@/features/projects/utils";
import { getAdapter, listAgents } from "@/lib/api/agents";
import { executeBenchmark, getBenchmark } from "@/lib/api/benchmarks";
import { ApiError } from "@/lib/api/client";
import { listPlatforms, pinnablePlatformVersions } from "@/lib/api/platforms";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

type Step = "configure" | "review";

function preferredPinnableVersionId(
  versions: { id: string; status: string; version_number: number }[],
  activeVersionId: string | null | undefined,
): string {
  const pinnable = versions.filter((v) => isPinnableVersionStatus(v.status));
  const preferred =
    pinnable.find((version) => version.id === activeVersionId) ??
    pinnable.find((version) => version.status === "active") ??
    pinnable[0];
  return preferred?.id ?? "";
}

export function BenchmarkDetailPage({
  projectId,
  suiteId,
}: {
  projectId: string;
  suiteId: string;
}) {
  const { token } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("configure");
  const [agentId, setAgentId] = useState("");
  const [agentVersionId, setAgentVersionId] = useState("");
  const [adapterVersionId, setAdapterVersionId] = useState("");
  const [platformId, setPlatformId] = useState("");
  const [platformVersionId, setPlatformVersionId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const suiteQuery = useQuery({
    queryKey: ["benchmark", suiteId],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getBenchmark(token, suiteId);
    },
  });

  const agentsQuery = useQuery({
    queryKey: [...agentsQueryKey, "list", "benchmark-execute"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listAgents(token, { limit: 100, sort: "-created_at" });
    },
  });

  const platformsQuery = useQuery({
    queryKey: ["platforms", "list", "benchmark-execute"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listPlatforms(token, { limit: 100 });
    },
  });

  const selectedAgent = agentsQuery.data?.items.find((agent) => agent.id === agentId);
  const adapterId = selectedAgent?.adapter_id ?? null;

  const adapterQuery = useQuery({
    queryKey: adapterId ? adapterQueryKey(adapterId) : ["adapters", "none"],
    enabled: Boolean(token) && Boolean(adapterId),
    queryFn: async () => {
      if (!token || !adapterId) throw new Error("Missing adapter");
      return getAdapter(token, adapterId);
    },
  });

  const selectedPlatform = platformsQuery.data?.items.find((p) => p.id === platformId);
  const agentVersions = useMemo(
    () =>
      (selectedAgent?.versions ?? [])
        .filter((v) => isPinnableVersionStatus(v.status))
        .slice()
        .sort((a, b) => b.version_number - a.version_number),
    [selectedAgent],
  );
  const adapterVersions = useMemo(
    () =>
      (adapterQuery.data?.versions ?? [])
        .filter((v) => isPinnableVersionStatus(v.status))
        .slice()
        .sort((a, b) => b.version_number - a.version_number),
    [adapterQuery.data],
  );
  const platformVersions = useMemo(
    () => (selectedPlatform ? pinnablePlatformVersions(selectedPlatform) : []),
    [selectedPlatform],
  );

  const suiteData = suiteQuery.data;
  const active = suiteData?.versions.find((v) => v.id === suiteData.active_version_id);
  const caseCount = active?.composition.length ?? 0;
  const agentLabel = selectedAgent?.name ?? "—";
  const adapterLabel = adapterQuery.data?.name ?? "—";
  const platformLabel = selectedPlatform
    ? `${selectedPlatform.name} / ${platformVersions.find((v) => v.id === platformVersionId)?.label ?? "—"}`
    : "—";

  const canReview =
    Boolean(suiteQuery.data?.active_version_id) &&
    Boolean(agentId) &&
    Boolean(agentVersionId) &&
    Boolean(adapterVersionId) &&
    Boolean(platformVersionId);

  const executeMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Missing auth token");
      const suite = suiteQuery.data;
      if (!suite?.active_version_id) throw new Error("No published benchmark version");
      return executeBenchmark(
        token,
        suiteId,
        suite.active_version_id,
        {
          agent_id: agentId,
          agent_version_id: agentVersionId,
          adapter_version_id: adapterVersionId,
          platform_version_id: platformVersionId,
        },
        crypto.randomUUID(),
      );
    },
    onSuccess: (execution) => {
      toast.success(`Queued ${String(execution.total_cases)} benchmark runs`);
      void queryClient.invalidateQueries({ queryKey: ["benchmark-results"] });
      router.push(
        `/projects/${projectId}/benchmarks/${suiteId}/executions/${execution.execution_group_id}?version=${execution.suite_version_id}`,
      );
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : "Failed to execute benchmark";
      setFormError(message);
      toast.error(message);
    },
  });

  if (projectQuery.isLoading || suiteQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (suiteQuery.isError) {
    if (suiteQuery.error instanceof ApiError && suiteQuery.error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="benchmark"
            action={
              <Button asChild variant="outline">
                <Link href={`/projects/${projectId}/benchmarks`}>Back</Link>
              </Button>
            }
          />
        </PageLayout>
      );
    }
    return (
      <PageLayout>
        <ErrorContent
          fill
          title="Couldn’t load benchmark"
          description={
            suiteQuery.error instanceof ApiError
              ? suiteQuery.error.message
              : "Something went wrong."
          }
        />
      </PageLayout>
    );
  }

  const suite = suiteQuery.data;
  if (!suite) return null;

  return (
    <PageLayout>
      <PageHeader
        eyebrow={projectQuery.data?.name ?? "Project"}
        title={suite.name}
        description={
          suite.description.trim()
            ? suite.description
            : "Immutable multi-case benchmark definition."
        }
        actions={
          <Cluster gap={2}>
            {suite.catalog_visible ? <Badge status="success">Catalog</Badge> : null}
            {suite.catalog_key ? <Badge status="neutral">{suite.catalog_key}</Badge> : null}
            <Button asChild variant="outline">
              <Link href={`/projects/${projectId}/suites/${suiteId}`}>Suite view</Link>
            </Button>
          </Cluster>
        }
      />

      <Section className="mt-8" title="Benchmark definition">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div>
            <Text as="div" variant="caption">
              Cases
            </Text>
            <Text as="div" variant="body">
              {String(caseCount)}
            </Text>
          </div>
          <div>
            <Text as="div" variant="caption">
              Catalog key
            </Text>
            <Text as="div" variant="body">
              {suite.catalog_key ?? "—"}
            </Text>
          </div>
          <div>
            <Text as="div" variant="caption">
              Active version
            </Text>
            <Text as="div" variant="body">
              {active ? `v${String(active.version_number)}` : "None published"}
            </Text>
          </div>
          <div>
            <Text as="div" variant="caption">
              Grader
            </Text>
            <Text as="div" variant="body">
              Workspace pytest (per case)
            </Text>
          </div>
        </dl>
        {active ? (
          <ul className="mt-4 divide-y divide-border">
            {active.composition
              .slice()
              .sort((a, b) => a.position - b.position)
              .map((entry) => (
                <li key={entry.case_version_id} className="py-2">
                  <Text as="div" variant="caption">
                    #{entry.position + 1} · case version {entry.case_version_id}
                  </Text>
                </li>
              ))}
          </ul>
        ) : null}
      </Section>

      {step === "configure" ? (
        <Section className="mt-10" title="Configure execution">
          <Text variant="secondary" className="mb-4">
            Select published agent, adapter, and platform pins. Live Gemini requires worker{" "}
            <code>WORKER_ADAPTER_MODE=live</code> and credentials — this UI does not change worker
            mode.
          </Text>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span>Agent</span>
              <Select
                value={agentId || undefined}
                onValueChange={(value) => {
                  setAgentId(value);
                  const agent = agentsQuery.data?.items.find((item) => item.id === value);
                  setAgentVersionId(
                    preferredPinnableVersionId(agent?.versions ?? [], agent?.active_version_id),
                  );
                  setAdapterVersionId("");
                  setFormError(null);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select agent" />
                </SelectTrigger>
                <SelectContent>
                  {(agentsQuery.data?.items ?? []).map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>

            <label className="grid gap-1 text-sm">
              <span>Agent version</span>
              <Select
                value={agentVersionId || undefined}
                onValueChange={(value) => {
                  setAgentVersionId(value);
                  setFormError(null);
                }}
                disabled={!agentId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select agent version" />
                </SelectTrigger>
                <SelectContent>
                  {agentVersions.map((version) => (
                    <SelectItem key={version.id} value={version.id}>
                      {version.label} ({version.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>

            <label className="grid gap-1 text-sm">
              <span>Adapter</span>
              <Text as="div" variant="body" className="rounded-md border border-border px-3 py-2">
                {adapterQuery.isLoading
                  ? "Loading…"
                  : (adapterQuery.data?.name ?? (agentId ? "No adapter connected" : "—"))}
              </Text>
            </label>

            <label className="grid gap-1 text-sm">
              <span>Adapter version</span>
              <Select
                value={adapterVersionId || undefined}
                onValueChange={(value) => {
                  setAdapterVersionId(value);
                  setFormError(null);
                }}
                disabled={!adapterId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select adapter version" />
                </SelectTrigger>
                <SelectContent>
                  {adapterVersions.map((version) => (
                    <SelectItem key={version.id} value={version.id}>
                      {version.label} ({version.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>

            <label className="grid gap-1 text-sm">
              <span>Platform</span>
              <Select
                value={platformId || undefined}
                onValueChange={(value) => {
                  setPlatformId(value);
                  const platform = platformsQuery.data?.items.find((item) => item.id === value);
                  const versions = platform ? pinnablePlatformVersions(platform) : [];
                  setPlatformVersionId(
                    preferredPinnableVersionId(versions, platform?.active_version_id),
                  );
                  setFormError(null);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {(platformsQuery.data?.items ?? []).map((platform) => (
                    <SelectItem key={platform.id} value={platform.id}>
                      {platform.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>

            <label className="grid gap-1 text-sm">
              <span>Platform version</span>
              <Select
                value={platformVersionId || undefined}
                onValueChange={(value) => {
                  setPlatformVersionId(value);
                  setFormError(null);
                }}
                disabled={!platformId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select platform version" />
                </SelectTrigger>
                <SelectContent>
                  {platformVersions.map((version) => (
                    <SelectItem key={version.id} value={version.id}>
                      {version.label} ({version.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
          </div>
          {formError ? (
            <InlineError className="mt-4" density="block">
              {formError}
            </InlineError>
          ) : null}
          <div className="mt-6">
            <Button
              type="button"
              disabled={!canReview}
              onClick={() => {
                setStep("review");
                setFormError(null);
              }}
            >
              Review execution
            </Button>
          </div>
        </Section>
      ) : (
        <Section className="mt-10" title="Review">
          <Text variant="secondary" className="mb-4">
            You are about to evaluate {agentLabel} ({adapterLabel}) against {String(caseCount)}{" "}
            pinned coding tasks in {suite.name}.
          </Text>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <Text as="div" variant="caption">
                Benchmark
              </Text>
              <Text as="div" variant="body">
                {suite.name}
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Cases
              </Text>
              <Text as="div" variant="body">
                {String(caseCount)}
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Agent
              </Text>
              <Text as="div" variant="body">
                {agentLabel}
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Adapter
              </Text>
              <Text as="div" variant="body">
                {adapterLabel}
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Platform
              </Text>
              <Text as="div" variant="body">
                {platformLabel}
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Execution
              </Text>
              <Text as="div" variant="body">
                Live (worker mode)
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Grader
              </Text>
              <Text as="div" variant="body">
                Workspace pytest
              </Text>
            </div>
            <div>
              <Text as="div" variant="caption">
                Repository pins
              </Text>
              <Text as="div" variant="body">
                Exact SHA per case version
              </Text>
            </div>
          </dl>
          {formError ? (
            <InlineError className="mt-4" density="block">
              {formError}
            </InlineError>
          ) : null}
          <Cluster gap={2} className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setStep("configure");
              }}
            >
              Back
            </Button>
            <Button
              type="button"
              disabled={executeMutation.isPending}
              onClick={() => {
                executeMutation.mutate();
              }}
            >
              {executeMutation.isPending ? "Queuing…" : "Run Benchmark"}
            </Button>
          </Cluster>
        </Section>
      )}
    </PageLayout>
  );
}
