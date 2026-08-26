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

  return (
    <PageLayout>
      <PageHeader
        eyebrow="Benchmark execution"
        title={inFlight ? "Running…" : "Results"}
        description={`Execution group ${executionGroupId}`}
        actions={
          <Button asChild variant="outline">
            <Link href={`/projects/${projectId}/benchmarks/${suiteId}`}>Back to benchmark</Link>
          </Button>
        }
      />

      <Section className="mt-8">
        <Cluster gap={3} className="flex-wrap">
          <Badge status="success">{results.passed} passed</Badge>
          <Badge status="warning">{results.evaluation_failed} eval failed</Badge>
          <Badge status="danger">{results.execution_failed} exec failed</Badge>
          <Badge status="neutral">pass rate {pct(results.pass_rate)}</Badge>
          <Badge status="neutral">
            {results.completed}/{results.total_cases} completed
          </Badge>
          {inFlight ? <Badge status="queued">in progress</Badge> : null}
        </Cluster>
      </Section>

      <Section className="mt-8" title="Cases">
        <ul className="divide-y divide-border">
          {results.cases.map((row) => (
            <li
              key={row.run_id}
              className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <Text as="div" variant="body" className="font-medium">
                  {row.case_version_id}
                </Text>
                <Text as="div" variant="caption">
                  {row.status}
                  {row.aggregate.passed === true
                    ? " · PASS"
                    : row.aggregate.passed === false
                      ? " · FAIL"
                      : ""}
                  {row.failure_category ? ` · ${row.failure_category}` : ""}
                </Text>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link href={`/runs/${row.run_id}`}>Open run</Link>
              </Button>
            </li>
          ))}
        </ul>
      </Section>
    </PageLayout>
  );
}
