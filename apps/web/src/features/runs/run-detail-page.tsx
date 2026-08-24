"use client";

import { Button, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ArtifactViewer } from "./artifact-viewer";
import { CancelRunDialog } from "./cancel-run-dialog";
import { ExecutionHeader } from "./execution-header";
import { ExecutionTimeline } from "./execution-timeline";
import { useRun, useRunArtifacts, useRunEvents, useRunPolling, useRunScores } from "./hooks";
import { ScoreViewer } from "./score-viewer";
import { runPassSignal, runStatusLabel, sortEventsBySequence, truncateId } from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { agentsQueryKey } from "@/features/agents/utils";
import { casesQueryKey } from "@/features/cases/utils";
import { projectQueryKey } from "@/features/projects/utils";
import { listAgents } from "@/lib/api/agents";
import { listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function RunDetailPage({ runId }: { runId: string }) {
  const { token } = useAuth();
  const [cancelOpen, setCancelOpen] = useState(false);

  const runQuery = useRun(runId);
  const status = runQuery.data?.status;
  const polling = useRunPolling(status);
  const eventsQuery = useRunEvents(runId, status, runQuery.isSuccess);
  const artifactsQuery = useRunArtifacts(runId, status, runQuery.isSuccess);
  const scoresQuery = useRunScores(runId, status, runQuery.isSuccess);

  const projectId = runQuery.data?.pins.project_id;

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId ?? ""),
    enabled: Boolean(token) && Boolean(projectId),
    queryFn: async () => {
      if (!token || !projectId) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const casesQuery = useQuery({
    queryKey: [...casesQueryKey(projectId ?? ""), "run-detail"],
    enabled: Boolean(token) && Boolean(projectId),
    queryFn: async () => {
      if (!token || !projectId) throw new Error("Missing auth token");
      return listCases(token, { project_id: projectId, limit: 100 });
    },
  });

  const agentsQuery = useQuery({
    queryKey: [...agentsQueryKey, "run-detail"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listAgents(token, { limit: 100 });
    },
  });

  const caseLabel = useMemo(() => {
    const caseVersionId = runQuery.data?.pins.case_version_id;
    if (!caseVersionId) return undefined;
    for (const caseItem of casesQuery.data?.items ?? []) {
      for (const version of caseItem.versions) {
        if (version.id === caseVersionId) {
          return `${caseItem.name} · v${String(version.version_number)}`;
        }
      }
    }
    return undefined;
  }, [casesQuery.data, runQuery.data?.pins.case_version_id]);

  const agentLabel = useMemo(() => {
    const agentVersionId = runQuery.data?.pins.agent_version_id;
    if (!agentVersionId) return undefined;
    for (const agent of agentsQuery.data?.items ?? []) {
      for (const version of agent.versions) {
        if (version.id === agentVersionId) {
          return `${agent.name} · v${String(version.version_number)}`;
        }
      }
    }
    return undefined;
  }, [agentsQuery.data, runQuery.data?.pins.agent_version_id]);

  if (runQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (runQuery.isError) {
    const error = runQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="run"
            action={
              <Button asChild variant="outline">
                <Link href="/runs">Back to runs</Link>
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
                <Link href="/runs">Back to runs</Link>
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
          title="Couldn’t load run"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this run."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void runQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const run = runQuery.data;
  if (!run) return null;

  const events = sortEventsBySequence(eventsQuery.data?.items ?? []);
  const artifacts = artifactsQuery.data?.items ?? [];
  const scores = scoresQuery.data?.items ?? run.scores;
  const pins = run.pins;
  const passed = runPassSignal({ scores });

  return (
    <PageLayout width="full" className="max-w-6xl">
      <FadeIn>
        <PageHeader
          eyebrow="Evaluation"
          title={
            passed === true ? "Passed" : passed === false ? "Failed" : runStatusLabel(run.status)
          }
          description={[
            agentLabel,
            projectQuery.data?.name,
            caseLabel,
            polling.isLive ? "Live observability" : "Immutable execution record",
          ]
            .filter(Boolean)
            .join(" · ")}
          actions={
            <Button asChild variant="outline">
              <Link href={`/runs/new?project=${encodeURIComponent(pins.project_id)}`}>
                Launch another
              </Link>
            </Button>
          }
        />

        <div className="mt-6 space-y-6">
          <ExecutionHeader
            run={{ ...run, scores }}
            events={events}
            {...(projectQuery.data?.name ? { projectName: projectQuery.data.name } : {})}
            {...(caseLabel ? { caseLabel } : {})}
            {...(agentLabel ? { agentLabel } : {})}
            onCancel={() => {
              setCancelOpen(true);
            }}
            onCopyId={() => {
              void navigator.clipboard.writeText(run.id).then(
                () => {
                  toast.success("Run ID copied");
                },
                () => {
                  toast.error("Could not copy run ID");
                },
              );
            }}
          />

          {(run.failure_reason ?? run.cancellation_reason) && (
            <section
              aria-label="Failure information"
              className="rounded-[var(--ef-radius-panel)] border border-danger/40 bg-danger-muted/40 px-4 py-3"
            >
              <Text
                as="div"
                variant="caption"
                className="font-mono uppercase tracking-[0.12em] text-danger"
              >
                {run.failure_reason ? "Failure" : "Cancellation"}
              </Text>
              {run.failure_reason ? (
                <Text variant="secondary" className="mt-2 whitespace-pre-wrap text-foreground">
                  {run.failure_reason}
                </Text>
              ) : null}
              {run.cancellation_reason ? (
                <Text variant="secondary" className="mt-2 whitespace-pre-wrap text-foreground">
                  {run.cancellation_reason}
                </Text>
              ) : null}
            </section>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <Section
              title="Execution timeline"
              className="lg:col-span-2"
              description="Events in sequence with expandable detail."
            >
              <ExecutionTimeline
                events={events}
                status={run.status}
                startedAt={run.created_at}
                isLoading={eventsQuery.isLoading}
                errorMessage={
                  eventsQuery.isError
                    ? eventsQuery.error instanceof ApiError
                      ? eventsQuery.error.message
                      : "Couldn’t load events."
                    : null
                }
                onRetry={() => {
                  void eventsQuery.refetch();
                }}
              />
            </Section>

            <Section title="Scores" description="Grader outcomes for this run.">
              <ScoreViewer
                scores={scores}
                expectedGraderCount={run.expected_grader_count}
                isPartiallyGraded={run.is_partially_graded}
                isLoading={scoresQuery.isLoading}
                errorMessage={
                  scoresQuery.isError
                    ? scoresQuery.error instanceof ApiError
                      ? scoresQuery.error.message
                      : "Couldn’t load scores."
                    : null
                }
                onRetry={() => {
                  void scoresQuery.refetch();
                }}
              />
            </Section>

            <Section
              title="Artifacts"
              className="lg:col-span-3"
              description="Evidence produced during execution — download stored bytes or inspect metadata."
            >
              <ArtifactViewer
                artifacts={artifacts}
                events={events}
                isLoading={artifactsQuery.isLoading}
                errorMessage={
                  artifactsQuery.isError
                    ? artifactsQuery.error instanceof ApiError
                      ? artifactsQuery.error.message
                      : "Couldn’t load artifacts."
                    : null
                }
                onRetry={() => {
                  void artifactsQuery.refetch();
                }}
              />
            </Section>

            <Section
              title="Pins & runtime"
              className="lg:col-span-3"
              description="Immutable version pins and sandbox bookkeeping."
            >
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetaField
                  label="Refresh"
                  value={polling.isLive ? "Polling every 2.5s" : "Idle (terminal)"}
                />
                <MetaField label="Sandbox" value={run.sandbox_id ?? "—"} mono />
                <MetaField label="Expected graders" value={String(run.expected_grader_count)} />
                <MetaField label="Produced scores" value={String(run.produced_score_count)} />
                <MetaField label="Outcome" value={runStatusLabel(run.status)} />
                <MetaField
                  label="Pass signal"
                  value={passed === null ? "—" : passed ? "Passed" : "Failed"}
                />
                <MetaField label="Run ID" value={run.id} mono />
                <MetaField label="Platform" value={pins.platform_version_id} mono />
              </div>
              <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-border pt-4">
                <PinLine
                  label="Project"
                  value={pins.project_id}
                  href={`/projects/${pins.project_id}`}
                />
                <PinLine label="Case version" value={pins.case_version_id} />
                <PinLine label="Prompt version" value={pins.prompt_version_id} />
                <PinLine label="Agent version" value={pins.agent_version_id} />
                <PinLine label="Adapter version" value={pins.adapter_version_id} />
                {pins.suite_version_id ? (
                  <PinLine label="Suite version" value={pins.suite_version_id} />
                ) : null}
              </ul>
            </Section>
          </div>
        </div>
      </FadeIn>

      <CancelRunDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        runId={run.id}
        projectId={pins.project_id}
        statusLabel={runStatusLabel(run.status)}
      />
    </PageLayout>
  );
}

function MetaField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.1em]">
        {label}
      </Text>
      <Text
        as="div"
        variant="body"
        className={mono ? "break-all font-mono text-[length:var(--ef-text-caption)]" : undefined}
      >
        {value}
      </Text>
    </div>
  );
}

function PinLine({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <li className="flex min-w-0 flex-wrap gap-2">
      <Text as="span" variant="caption">
        {label}
      </Text>
      {href ? (
        <Link
          href={href}
          className="break-all font-mono text-[length:var(--ef-text-caption)] text-accent underline-offset-2 hover:underline"
        >
          {truncateId(value, 16)}
        </Link>
      ) : (
        <Text
          as="span"
          variant="body"
          className="break-all font-mono text-[length:var(--ef-text-caption)]"
        >
          {truncateId(value, 16)}
        </Text>
      )}
    </li>
  );
}
