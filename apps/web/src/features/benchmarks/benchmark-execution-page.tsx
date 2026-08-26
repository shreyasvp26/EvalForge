"use client";

import { Badge, Button, Cluster, Text } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { getBenchmarkResults } from "@/lib/api/benchmarks";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

function pct(value: number | null): string {
  if (value == null) return "—";
  return `${String(Math.round(value * 1000) / 10)}%`;
}

function caseGlyph(status: string, passed: boolean | null): string {
  if (status === "completed") {
    if (passed === true) return "✓";
    if (passed === false) return "✗";
    return "•";
  }
  if (status === "failed" || status === "cancelled") return "!";
  if (status === "running" || status === "grading" || status === "claimed") return "●";
  return "○";
}

function caseResultLabel(status: string, passed: boolean | null): string {
  if (status === "completed") {
    if (passed === true) return "PASS";
    if (passed === false) return "FAIL";
    return "COMPLETED";
  }
  if (status === "failed") return "EXEC FAIL";
  if (status === "cancelled") return "CANCELLED";
  if (status === "running" || status === "grading" || status === "claimed") {
    return "RUNNING";
  }
  return "QUEUED";
}

export function BenchmarkExecutionPage({
  projectId,
  suiteId,
  executionGroupId,
}: {
  projectId: string;
  suiteId: string;
  executionGroupId: string;
}) {
  const { token } = useAuth();
  const search = useSearchParams();
  const versionId = search.get("version") ?? "";

  const resultsQuery = useQuery({
    queryKey: ["benchmark-results", suiteId, versionId, executionGroupId],
    enabled: Boolean(token && versionId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (data.queued_or_running > 0) return 2000;
      return false;
    },
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getBenchmarkResults(token, suiteId, versionId, executionGroupId);
    },
  });

  if (!versionId) {
    return (
      <PageLayout>
        <ErrorContent
          fill
          title="Missing version"
          description="Open this page from a benchmark execute response."
        />
      </PageLayout>
    );
  }

  if (resultsQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (resultsQuery.isError) {
    return (
      <PageLayout>
        <ErrorContent
          fill
          title="Couldn’t load results"
          description={
            resultsQuery.error instanceof ApiError
              ? resultsQuery.error.message
              : "Something went wrong."
          }
        />
      </PageLayout>
    );
  }

  const results = resultsQuery.data;
  if (!results) return null;
  const inFlight = results.queued_or_running > 0;
  const decided = results.passed + results.evaluation_failed;
  const progressDone = results.completed + results.execution_failed + results.cancelled;
  const providerBlocked = results.cases.filter((row) => {
    const reason = (row.failure_reason ?? "").toLowerCase();
    return (
      reason.includes("quota") ||
      reason.includes("rate limit") ||
      reason.includes("rate_limit") ||
      reason.includes("authentication") ||
      reason.includes("api key") ||
      reason.includes("permission denied")
    );
  }).length;

  return (
    <PageLayout>
      <PageHeader
        eyebrow="Benchmark execution"
        title={inFlight ? "Running…" : "Results"}
        description={`How did this agent perform on this benchmark?`}
        actions={
          <Cluster gap={2}>
            {inFlight ? <Badge status="queued">Live polling</Badge> : null}
            <Button asChild variant="outline">
              <Link href={`/projects/${projectId}/benchmarks/${suiteId}`}>Back</Link>
            </Button>
          </Cluster>
        }
      />

      <Section className="mt-8" title="Overview">
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <Text as="div" variant="caption">
              Progress
            </Text>
            <Text as="div" variant="body">
              {String(progressDone)} / {String(results.total_cases)} finished
              {inFlight ? ` · ${String(results.queued_or_running)} in flight` : ""}
            </Text>
          </div>
          <div>
            <Text as="div" variant="caption">
              Overall (eval pass rate)
            </Text>
            <Text as="div" variant="body">
              {pct(results.pass_rate)}
              {decided > 0
                ? ` · ${String(results.passed)}/${String(decided)} decided`
                : " · no decided grades yet"}
            </Text>
          </div>
          <div>
            <Text as="div" variant="caption">
              Execution group
            </Text>
            <Text as="div" variant="body" className="break-all">
              {results.execution_group_id ?? executionGroupId}
            </Text>
          </div>
        </dl>
        <Cluster gap={3} className="mt-4 flex-wrap">
          <Badge status="success">{String(results.passed)} passed</Badge>
          <Badge status="warning">{String(results.evaluation_failed)} eval failed</Badge>
          <Badge status="danger">{String(results.execution_failed)} exec failed</Badge>
          {providerBlocked > 0 ? (
            <Badge status="danger">{String(providerBlocked)} provider-blocked</Badge>
          ) : null}
          {results.cancelled > 0 ? (
            <Badge status="neutral">{String(results.cancelled)} cancelled</Badge>
          ) : null}
        </Cluster>
        <Text variant="secondary" className="mt-3">
          Evaluation failures count against agent performance. Execution and provider failures do
          not become ordinary agent scores. Token/cost data is omitted when the provider does not
          report usage.
        </Text>
      </Section>

      <Section className="mt-8" title="Cases">
        <ul className="divide-y divide-border">
          {results.cases.map((row) => {
            const label = caseResultLabel(row.status, row.aggregate.passed);
            const glyph = caseGlyph(row.status, row.aggregate.passed);
            return (
              <li
                key={row.run_id}
                className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <Text as="div" variant="body" className="font-medium">
                    {glyph} {row.case_name ?? row.case_version_id}
                  </Text>
                  <Text as="div" variant="caption">
                    {[
                      row.category,
                      row.difficulty,
                      label,
                      row.aggregate.overall_score != null
                        ? `score ${String(row.aggregate.overall_score)}`
                        : null,
                      row.failure_category,
                      row.failure_reason,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/runs/${row.run_id}`}>Open run</Link>
                </Button>
              </li>
            );
          })}
        </ul>
      </Section>
    </PageLayout>
  );
}
