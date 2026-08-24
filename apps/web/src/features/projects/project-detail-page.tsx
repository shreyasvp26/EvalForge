"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { DeprecateProjectDialog } from "./deprecate-project-dialog";
import {
  formatProjectDate,
  projectQueryKey,
  projectStatusBadge,
  projectStatusLabel,
} from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { StatusBadge } from "@/components/status/status-badge";
import { casesQueryKey } from "@/features/cases/utils";
import { formatCount, primaryScoreLabel, runPassSignal } from "@/features/dashboard/utils";
import { truncateId } from "@/features/runs/utils";
import { suitesQueryKey } from "@/features/suites/utils";
import { listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { listRuns } from "@/lib/api/runs";
import { listSuites } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

const WORKSPACE_LIST_LIMIT = 8;
const RESOURCE_COUNT_LIMIT = 20;

function WorkspaceNavTile({
  href,
  label,
  description,
  countLabel,
}: {
  href: string;
  label: string;
  description: string;
  countLabel?: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-1 rounded-[var(--ef-radius-panel)] border border-border bg-card px-4 py-4 transition-colors hover:border-foreground/20 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-baseline justify-between gap-2">
        <Text as="span" variant="body" className="font-medium group-hover:underline">
          {label}
        </Text>
        {countLabel !== undefined ? (
          <Text as="span" variant="caption" className="tabular-nums text-muted-foreground">
            {countLabel}
          </Text>
        ) : null}
      </div>
      <Text as="span" variant="caption" className="text-muted-foreground">
        {description}
      </Text>
    </Link>
  );
}

export function ProjectDetailPage({ projectId }: { projectId: string }) {
  const { token } = useAuth();
  const [deprecateOpen, setDeprecateOpen] = useState(false);

  const query = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const runsQuery = useQuery({
    queryKey: ["projects", projectId, "runs", "workspace", WORKSPACE_LIST_LIMIT],
    enabled: Boolean(token) && Boolean(query.data),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRuns(token, {
        project_id: projectId,
        limit: WORKSPACE_LIST_LIMIT,
        sort: "-created_at",
      });
    },
  });

  const casesQuery = useQuery({
    queryKey: [...casesQueryKey(projectId), "count", RESOURCE_COUNT_LIMIT],
    enabled: Boolean(token) && Boolean(query.data),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listCases(token, {
        project_id: projectId,
        limit: RESOURCE_COUNT_LIMIT,
        sort: "-created_at",
      });
    },
  });

  const suitesQuery = useQuery({
    queryKey: [...suitesQueryKey(projectId), "count", RESOURCE_COUNT_LIMIT],
    enabled: Boolean(token) && Boolean(query.data),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listSuites(token, {
        project_id: projectId,
        limit: RESOURCE_COUNT_LIMIT,
        sort: "-created_at",
      });
    },
  });

  if (query.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (query.isError) {
    const error = query.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="project"
            action={
              <Button asChild variant="outline">
                <Link href="/projects">Back to projects</Link>
              </Button>
            }
          />
        </PageLayout>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageLayout>
          <PermissionDeniedState
            action={
              <Button asChild variant="outline">
                <Link href="/projects">Back to projects</Link>
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
          title="Couldn’t load project"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this project."
          }
          action={
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void query.refetch();
              }}
            >
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const project = query.data;
  if (!project) return null;

  const isDeprecated = project.status === "deprecated";
  const recentRuns = runsQuery.data?.items ?? [];
  const casesCountLabel = casesQuery.data
    ? formatCount(casesQuery.data.items.length, casesQuery.data.has_more)
    : undefined;
  const suitesCountLabel = suitesQuery.data
    ? formatCount(suitesQuery.data.items.length, suitesQuery.data.has_more)
    : undefined;

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow="Evaluation workspace"
          title={project.name}
          description={
            project.description.trim()
              ? project.description
              : "No description provided for this workspace."
          }
          actions={
            <Cluster gap={2}>
              {!isDeprecated ? (
                <Button asChild>
                  <Link href={`/runs/new?project=${encodeURIComponent(project.id)}`}>
                    Launch run
                  </Link>
                </Button>
              ) : null}
              {!isDeprecated ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setDeprecateOpen(true);
                  }}
                >
                  Deprecate
                </Button>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  void navigator.clipboard.writeText(project.id).then(
                    () => {
                      toast.success("Project ID copied");
                    },
                    () => {
                      toast.error("Could not copy project ID");
                    },
                  );
                }}
              >
                Copy ID
              </Button>
            </Cluster>
          }
        />

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Badge status={projectStatusBadge(project.status)}>
            {projectStatusLabel(project.status)}
          </Badge>
          <Text variant="caption" className="tabular-nums text-muted-foreground">
            Created {formatProjectDate(project.created_at)}
          </Text>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <Section
            title="Workspace"
            className="lg:col-span-3"
            description="Cases, suites, and settings for this evaluation project."
          >
            <div className="grid gap-3 sm:grid-cols-3">
              <WorkspaceNavTile
                href={`/projects/${project.id}/cases`}
                label="Cases"
                description="Evaluation specs and prompts"
                {...(casesCountLabel !== undefined ? { countLabel: casesCountLabel } : {})}
              />
              <WorkspaceNavTile
                href={`/projects/${project.id}/suites`}
                label="Suites"
                description="Grouped case compositions"
                {...(suitesCountLabel !== undefined ? { countLabel: suitesCountLabel } : {})}
              />
              <WorkspaceNavTile
                href={`/projects/${project.id}/settings`}
                label="Settings"
                description="Project configuration"
              />
            </div>
          </Section>

          <Section
            title="Recent runs"
            className="lg:col-span-3"
            description="Latest evaluations launched in this workspace."
            actions={
              <Button asChild size="sm" variant="ghost">
                <Link href={`/runs?project=${encodeURIComponent(project.id)}`}>View all runs</Link>
              </Button>
            }
          >
            {runsQuery.isLoading ? (
              <Text variant="secondary">Loading runs…</Text>
            ) : runsQuery.isError ? (
              <Text variant="secondary">
                {runsQuery.error instanceof ApiError
                  ? runsQuery.error.message
                  : "Couldn’t load runs for this project."}
              </Text>
            ) : recentRuns.length === 0 ? (
              <div className="space-y-3">
                <Text variant="secondary">
                  No runs yet. Launch a run to evaluate cases in this workspace.
                </Text>
                {!isDeprecated ? (
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/runs/new?project=${encodeURIComponent(project.id)}`}>
                      Launch run
                    </Link>
                  </Button>
                ) : null}
              </div>
            ) : (
              <div className="overflow-x-auto rounded-[var(--ef-radius-panel)] border border-border">
                <table className="w-full min-w-[32rem] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-border bg-muted/40">
                      <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                        Status
                      </th>
                      <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                        Run
                      </th>
                      <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                        Score
                      </th>
                      <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                        Created
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRuns.map((run) => {
                      const score = primaryScoreLabel(run);
                      const passed = runPassSignal(run);
                      return (
                        <tr key={run.id} className="border-b border-border last:border-b-0">
                          <td className="px-3 py-2.5">
                            <StatusBadge status={run.status} passed={passed} size="sm" />
                          </td>
                          <td className="px-3 py-2.5">
                            <Link
                              href={`/runs/${run.id}`}
                              className="font-mono text-[length:var(--ef-text-caption)] text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              {truncateId(run.id, 14)}
                            </Link>
                          </td>
                          <td className="px-3 py-2.5 font-mono text-[length:var(--ef-text-caption)] tabular-nums">
                            {score ?? "—"}
                          </td>
                          <td className="px-3 py-2.5 text-[length:var(--ef-text-caption)] tabular-nums text-muted-foreground">
                            {formatProjectDate(run.created_at)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </div>
      </FadeIn>

      <DeprecateProjectDialog
        open={deprecateOpen}
        onOpenChange={setDeprecateOpen}
        projectId={project.id}
        projectName={project.name}
      />
    </PageLayout>
  );
}
