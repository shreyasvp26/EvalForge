"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { CancelRunDialog } from "./cancel-run-dialog";
import {
  canCancelRun,
  durationFromEvents,
  formatRunDate,
  runArtifactsQueryKey,
  runEventsQueryKey,
  runQueryKey,
  runScoresQueryKey,
  runStatusBadge,
  runStatusLabel,
  sortEventsBySequence,
  truncateId,
} from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { ApiError } from "@/lib/api/client";
import { getRun, listRunArtifacts, listRunEvents, listRunScores } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function RunDetailPage({ runId }: { runId: string }) {
  const { token } = useAuth();
  const [cancelOpen, setCancelOpen] = useState(false);

  const runQuery = useQuery({
    queryKey: runQueryKey(runId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getRun(token, runId);
    },
  });

  const eventsQuery = useQuery({
    queryKey: runEventsQueryKey(runId),
    enabled: Boolean(token) && runQuery.isSuccess,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunEvents(token, runId, { limit: 100, sort: "sequence" });
    },
  });

  const artifactsQuery = useQuery({
    queryKey: runArtifactsQueryKey(runId),
    enabled: Boolean(token) && runQuery.isSuccess,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunArtifacts(token, runId, { limit: 100, sort: "-created_at" });
    },
  });

  const scoresQuery = useQuery({
    queryKey: runScoresQueryKey(runId),
    enabled: Boolean(token) && runQuery.isSuccess,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunScores(token, runId, { limit: 100 });
    },
  });

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
  const duration = durationFromEvents(events);
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
          eyebrow="Run"
          title={truncateId(run.id, 18)}
          description="Immutable pins and execution outcome for this evaluation run."
          actions={
            <Cluster gap={2}>
              {canCancelRun(run.status) ? (
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => {
                    setCancelOpen(true);
                  }}
                >
                  Cancel run
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void navigator.clipboard.writeText(run.id).then(
                    () => {
                      toast.success("Run ID copied");
                    },
                    () => {
                      toast.error("Could not copy run ID");
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
          <Badge status={runStatusBadge(run.status)}>{runStatusLabel(run.status)}</Badge>
          <Text variant="caption" className="tabular-nums">
            Created {formatRunDate(run.created_at)}
          </Text>
          <Text variant="caption" className="tabular-nums">
            Duration {duration}
          </Text>
          {run.is_partially_graded ? <Badge status="warning">Partially graded</Badge> : null}
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
            title="Pinned versions"
            className="lg:col-span-2"
            description="Immutable references established at launch. These do not change after create."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <PinField
                label="Project"
                value={pins.project_id}
                href={`/projects/${pins.project_id}`}
              />
              <PinField label="Case version" value={pins.case_version_id} />
              <PinField label="Prompt version" value={pins.prompt_version_id} />
              <PinField label="Agent version" value={pins.agent_version_id} />
              <PinField label="Adapter version" value={pins.adapter_version_id} />
              <PinField label="Platform version" value={pins.platform_version_id} />
              {pins.suite_version_id ? (
                <PinField label="Suite version" value={pins.suite_version_id} />
              ) : null}
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Grader versions
                </Text>
                {pins.grader_version_ids.length === 0 ? (
                  <Text variant="secondary">None</Text>
                ) : (
                  <ul className="space-y-1">
                    {pins.grader_version_ids.map((id) => (
                      <li key={id}>
                        <Text
                          as="span"
                          variant="body"
                          className="break-all font-mono text-[length:var(--ef-text-caption)]"
                        >
                          {id}
                        </Text>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </dl>
          </Section>

          <Section title="Metadata" description="Mutable run bookkeeping from the Control Plane.">
            <dl className="space-y-4">
              <MetaField label="Sandbox" value={run.sandbox_id ?? "—"} mono />
              <MetaField label="Expected graders" value={String(run.expected_grader_count)} />
              <MetaField label="Produced scores" value={String(run.produced_score_count)} />
              <MetaField label="Run ID" value={run.id} mono />
            </dl>
          </Section>

          <Section
            title="Timeline"
            className="lg:col-span-3"
            description="Execution events in sequence order."
          >
            {eventsQuery.isLoading ? (
              <Text variant="secondary">Loading events…</Text>
            ) : eventsQuery.isError ? (
              <ErrorContent
                title="Couldn’t load events"
                description={
                  eventsQuery.error instanceof ApiError
                    ? eventsQuery.error.message
                    : "Something went wrong."
                }
                action={
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void eventsQuery.refetch()}
                  >
                    Try again
                  </Button>
                }
              />
            ) : events.length === 0 ? (
              <Text variant="secondary">
                No events recorded yet. Events appear as the worker progresses.
              </Text>
            ) : (
              <ol className="relative space-y-0 border-l border-border pl-6">
                {events.map((event) => (
                  <li key={event.id} className="relative pb-6 last:pb-0">
                    <span
                      className="absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 rounded-full border border-border bg-card"
                      aria-hidden
                    />
                    <Cluster gap={2} className="items-center">
                      <Text as="span" variant="body" className="font-medium">
                        {event.kind}
                      </Text>
                      <Text as="span" variant="caption" className="tabular-nums">
                        #{String(event.sequence)}
                      </Text>
                      <Text as="span" variant="caption" className="tabular-nums">
                        {formatRunDate(event.occurred_at)}
                      </Text>
                    </Cluster>
                    {Object.keys(event.action).length > 0 ? (
                      <pre className="mt-2 max-h-40 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-2 font-mono text-[length:var(--ef-text-caption)] whitespace-pre-wrap break-words">
                        {JSON.stringify(event.action, null, 2)}
                      </pre>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </Section>

          <Section
            title="Artifacts"
            className="lg:col-span-3"
            description="Stored outputs associated with this run."
          >
            {artifactsQuery.isLoading ? (
              <Text variant="secondary">Loading artifacts…</Text>
            ) : artifactsQuery.isError ? (
              <ErrorContent
                title="Couldn’t load artifacts"
                description={
                  artifactsQuery.error instanceof ApiError
                    ? artifactsQuery.error.message
                    : "Something went wrong."
                }
                action={
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void artifactsQuery.refetch()}
                  >
                    Try again
                  </Button>
                }
              />
            ) : artifacts.length === 0 ? (
              <Text variant="secondary">No artifacts yet.</Text>
            ) : (
              <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
                {artifacts.map((artifact) => (
                  <li key={artifact.id} className="grid gap-1 px-4 py-3 sm:grid-cols-4">
                    <Text as="div" variant="body" className="font-medium">
                      {artifact.kind}
                    </Text>
                    <Text as="div" variant="caption" className="break-all font-mono sm:col-span-2">
                      {artifact.storage_key}
                    </Text>
                    <Text as="div" variant="caption" className="tabular-nums sm:text-right">
                      {String(artifact.size_bytes)} B · {artifact.content_type}
                    </Text>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section
            title="Scores"
            className="lg:col-span-3"
            description="Grader outputs for this run."
          >
            {scoresQuery.isLoading ? (
              <Text variant="secondary">Loading scores…</Text>
            ) : scoresQuery.isError ? (
              <ErrorContent
                title="Couldn’t load scores"
                description={
                  scoresQuery.error instanceof ApiError
                    ? scoresQuery.error.message
                    : "Something went wrong."
                }
                action={
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void scoresQuery.refetch()}
                  >
                    Try again
                  </Button>
                }
              />
            ) : scores.length === 0 ? (
              <Text variant="secondary">No scores yet.</Text>
            ) : (
              <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
                {scores.map((score) => (
                  <li key={score.id} className="grid gap-2 px-4 py-3 sm:grid-cols-3">
                    <div>
                      <Text as="div" variant="caption">
                        Grader
                      </Text>
                      <Text
                        as="div"
                        variant="body"
                        className="break-all font-mono text-[length:var(--ef-text-caption)]"
                      >
                        {score.grader_id}
                      </Text>
                    </div>
                    <div>
                      <Text as="div" variant="caption">
                        Version
                      </Text>
                      <Text
                        as="div"
                        variant="body"
                        className="break-all font-mono text-[length:var(--ef-text-caption)]"
                      >
                        {score.grader_version_id}
                      </Text>
                    </div>
                    <div>
                      <Text as="div" variant="caption">
                        Value
                      </Text>
                      <Text as="div" variant="body">
                        {formatScoreValue(score.value)}
                      </Text>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Quick actions">
            <Cluster gap={2} className="flex-col items-stretch sm:items-start">
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
            </Cluster>
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

function PinField({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div className="space-y-1">
      <Text as="div" variant="caption">
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
          as="div"
          variant="body"
          className="break-all font-mono text-[length:var(--ef-text-caption)]"
        >
          {value}
        </Text>
      )}
    </div>
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

function formatScoreValue(value: {
  numeric: number | null;
  categorical: string | null;
  passed: boolean | null;
}): string {
  const parts: string[] = [];
  if (value.numeric !== null) parts.push(String(value.numeric));
  if (value.categorical) parts.push(value.categorical);
  if (value.passed !== null) parts.push(value.passed ? "passed" : "failed");
  return parts.length > 0 ? parts.join(" · ") : "—";
}
