"use client";

import { Badge, Button, Cluster, Text, toast } from "@agent-eval/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { projectQueryKey } from "@/features/projects/utils";
import { executeBenchmark, getBenchmark } from "@/lib/api/benchmarks";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

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
  const [agentId, setAgentId] = useState("");
  const [agentVersionId, setAgentVersionId] = useState("");
  const [adapterVersionId, setAdapterVersionId] = useState("");
  const [platformVersionId, setPlatformVersionId] = useState("");

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

  const executeMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Missing auth token");
      const suite = suiteQuery.data;
      if (!suite?.active_version_id) throw new Error("No published benchmark version");
      return executeBenchmark(token, suiteId, suite.active_version_id, {
        agent_id: agentId.trim(),
        agent_version_id: agentVersionId.trim(),
        adapter_version_id: adapterVersionId.trim(),
        platform_version_id: platformVersionId.trim(),
      });
    },
    onSuccess: (execution) => {
      toast.success(`Queued ${String(execution.total_cases)} benchmark runs`);
      void queryClient.invalidateQueries({ queryKey: ["benchmark-results"] });
      router.push(
        `/projects/${projectId}/benchmarks/${suiteId}/executions/${execution.execution_group_id}?version=${execution.suite_version_id}`,
      );
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "Failed to execute benchmark");
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
  const active = suite.versions.find((v) => v.id === suite.active_version_id) ?? null;
  const canRun =
    Boolean(suite.active_version_id) &&
    agentId.trim() &&
    agentVersionId.trim() &&
    adapterVersionId.trim() &&
    platformVersionId.trim();

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

      <Section className="mt-8" title="Cases">
        {!active ? (
          <Text variant="secondary">No published version.</Text>
        ) : (
          <ul className="divide-y divide-border">
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
        )}
      </Section>

      <Section className="mt-10" title="Run benchmark">
        <Text variant="secondary" className="mb-4">
          Fans out one Run per case through the existing worker queue. Paste published agent /
          adapter / platform version IDs.
        </Text>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              ["Agent ID", agentId, setAgentId],
              ["Agent version ID", agentVersionId, setAgentVersionId],
              ["Adapter version ID", adapterVersionId, setAdapterVersionId],
              ["Platform version ID", platformVersionId, setPlatformVersionId],
            ] as const
          ).map(([label, value, setter]) => (
            <label key={label} className="grid gap-1 text-sm">
              <span>{label}</span>
              <input
                className="rounded-md border border-border bg-background px-3 py-2"
                value={value}
                onChange={(event) => {
                  setter(event.target.value);
                }}
              />
            </label>
          ))}
        </div>
        <div className="mt-4">
          <Button
            type="button"
            disabled={!canRun || executeMutation.isPending}
            onClick={() => {
              executeMutation.mutate();
            }}
          >
            {executeMutation.isPending ? "Queuing…" : "Run benchmark"}
          </Button>
        </div>
      </Section>
    </PageLayout>
  );
}
