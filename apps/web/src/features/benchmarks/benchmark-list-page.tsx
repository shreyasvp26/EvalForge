"use client";

import { Badge, Button, Cluster, FlaskConical, Text } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyContent } from "@/components/layouts/empty-content";
import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { projectQueryKey } from "@/features/projects/utils";
import { listBenchmarks } from "@/lib/api/benchmarks";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function BenchmarkListPage({ projectId }: { projectId: string }) {
  const { token } = useAuth();

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const catalogQuery = useQuery({
    queryKey: ["benchmarks", projectId],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listBenchmarks(token, projectId);
    },
  });

  const projectName = projectQuery.data?.name ?? "Project";

  return (
    <PageLayout>
      <PageHeader
        eyebrow={projectName}
        title="Benchmarks"
        description="Catalog-visible suites ready for reproducible multi-case evaluation."
        actions={
          <Button asChild variant="outline">
            <Link href={`/projects/${projectId}/suites`}>All suites</Link>
          </Button>
        }
      />

      <Section className="mt-8">
        {catalogQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load benchmarks"
            description={
              catalogQuery.error instanceof ApiError
                ? catalogQuery.error.message
                : "Something went wrong while loading the catalog."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void catalogQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : catalogQuery.isLoading ? (
          <EmptyContent
            fill
            icon={FlaskConical}
            title="Loading benchmarks…"
            description="Fetching catalog-visible suites for this project."
          />
        ) : (catalogQuery.data?.items.length ?? 0) === 0 ? (
          <EmptyContent
            fill
            icon={FlaskConical}
            title="No catalog benchmarks"
            description="Publish a suite, set catalog_visible, or seed Coding Benchmark v1."
          />
        ) : (
          <ul className="divide-y divide-border">
            {(catalogQuery.data?.items ?? []).map((entry) => (
              <li
                key={entry.suite_id}
                className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <Cluster gap={2} className="items-center">
                    <Text as="span" variant="body" className="font-medium">
                      {entry.name}
                    </Text>
                    <Badge status="neutral">{entry.catalog_key}</Badge>
                  </Cluster>
                  <Text as="div" variant="caption">
                    {entry.case_count} cases
                    {entry.categories.length ? ` · ${entry.categories.join(", ")}` : ""}
                    {entry.active_version_number != null
                      ? ` · v${String(entry.active_version_number)}`
                      : " · no published version"}
                  </Text>
                </div>
                <Button asChild size="sm">
                  <Link href={`/projects/${projectId}/benchmarks/${entry.suite_id}`}>Open</Link>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </PageLayout>
  );
}
