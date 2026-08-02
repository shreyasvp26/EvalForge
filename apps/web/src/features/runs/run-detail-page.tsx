"use client";

import { Button, FadeIn, Text, toast } from "@agent-eval/ui";
import Link from "next/link";
import { useState } from "react";

import { ArtifactViewer } from "./artifact-viewer";
import { CancelRunDialog } from "./cancel-run-dialog";
import { ExecutionHeader } from "./execution-header";
import { ExecutionTimeline } from "./execution-timeline";
import { useRun, useRunArtifacts, useRunEvents, useRunPolling, useRunScores } from "./hooks";
import { ScoreViewer } from "./score-viewer";
import { runStatusLabel, sortEventsBySequence, truncateId } from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { ApiError } from "@/lib/api/client";

export function RunDetailPage({ runId }: { runId: string }) {
  const [cancelOpen, setCancelOpen] = useState(false);

  const runQuery = useRun(runId);
  const status = runQuery.data?.status;
  const polling = useRunPolling(status);
  const eventsQuery = useRunEvents(runId, status, runQuery.isSuccess);
  const artifactsQuery = useRunArtifacts(runId, status, runQuery.isSuccess);
  const scoresQuery = useRunScores(runId, status, runQuery.isSuccess);

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

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          breadcrumbs={
            <Breadcrumbs
              items={[
                { label: "Workspace", href: "/projects" },
                { label: "Runs", href: "/runs" },
                { label: truncateId(run.id, 12) },
              ]}
            />
          }
          eyebrow="Live execution"
          title={truncateId(run.id, 18)}
          description={
            polling.isLive
              ? "Refreshing while queued, running, or grading. Updates stop at a terminal status."
              : "Read-only execution record. Pins are immutable; cancel is unavailable in terminal states."
          }
        />

        <div className="mt-6">
          <ExecutionHeader
            run={run}
            events={events}
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
        </div>

        {(run.failure_reason ?? run.cancellation_reason) && (
          <Section className="mt-6" title="Outcome notes">
            {run.failure_reason ? (
              <Text variant="secondary" className="whitespace-pre-wrap">
                Failure: {run.failure_reason}
              </Text>
            ) : null}
            {run.cancellation_reason ? (
              <Text variant="secondary" className="whitespace-pre-wrap">
                Cancellation: {run.cancellation_reason}
              </Text>
            ) : null}
          </Section>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <Section
            title="Timeline"
            className="lg:col-span-2"
            description="Grouped execution events with expandable details."
          >
            <ExecutionTimeline
              events={events}
              status={run.status}
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

          <Section title="Metadata" description="Mutable bookkeeping from the Control Plane.">
            <dl className="space-y-4">
              <MetaField label="Sandbox" value={run.sandbox_id ?? "—"} mono />
              <MetaField label="Expected graders" value={String(run.expected_grader_count)} />
              <MetaField label="Produced scores" value={String(run.produced_score_count)} />
              <MetaField
                label="Refresh"
                value={polling.isLive ? "Polling every 2.5s" : "Idle (terminal)"}
              />
              <MetaField label="Run ID" value={run.id} mono />
            </dl>

            <div className="mt-6 space-y-1">
              <Text as="div" variant="caption">
                Pinned versions
              </Text>
              <ul className="space-y-1">
                <PinLine
                  label="Project"
                  value={pins.project_id}
                  href={`/projects/${pins.project_id}`}
                />
                <PinLine label="Case" value={pins.case_version_id} />
                <PinLine label="Prompt" value={pins.prompt_version_id} />
                <PinLine label="Agent" value={pins.agent_version_id} />
                <PinLine label="Adapter" value={pins.adapter_version_id} />
                <PinLine label="Platform" value={pins.platform_version_id} />
                {pins.suite_version_id ? (
                  <PinLine label="Suite" value={pins.suite_version_id} />
                ) : null}
              </ul>
            </div>
          </Section>

          <Section
            title="Artifacts"
            className="lg:col-span-3"
            description="stdout, stderr, JSON, logs, and files — copy or download the available view."
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
            title="Scores"
            className="lg:col-span-3"
            description="Grader results with expandable metadata. Partial grading stays visible."
          >
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

          <Section title="Quick actions">
            <div className="flex flex-col items-stretch gap-2 sm:items-start">
              <Button asChild variant="outline" className="justify-start">
                <Link href="/runs">Back to runs</Link>
              </Button>
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/projects/${pins.project_id}`}>Open project</Link>
              </Button>
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/runs/new?project=${encodeURIComponent(pins.project_id)}`}>
                  Launch another run
                </Link>
              </Button>
            </div>
          </Section>
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
      <Text as="div" variant="caption">
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
    <li className="flex flex-wrap gap-2">
      <Text as="span" variant="caption">
        {label}
      </Text>
      {href ? (
        <Link
          href={href}
          className="break-all font-mono text-[length:var(--ef-text-caption)] text-accent underline-offset-2 hover:underline"
        >
          {value}
        </Link>
      ) : (
        <Text
          as="span"
          variant="body"
          className="break-all font-mono text-[length:var(--ef-text-caption)]"
        >
          {value}
        </Text>
      )}
    </li>
  );
}
