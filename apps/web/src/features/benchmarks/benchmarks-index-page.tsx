"use client";

import { Button, FlaskConical, FolderKanban, Text } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyContent } from "@/components/layouts/empty-content";
import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { projectsQueryKey } from "@/features/projects/utils";
import { ApiError } from "@/lib/api/client";
import { listProjects } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function BenchmarksIndexPage() {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: [...projectsQueryKey, "list", "benchmarks-index"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProjects(token, { limit: 100, sort: "-created_at" });
    },
  });

  return (
    <PageLayout>
      <PageHeader
        eyebrow="Evaluation"
        title="Benchmarks"
        description="Catalog-visible suites with immutable case pins. Choose a project to browse runnable benchmarks."
      />

      <Section className="mt-8">
        {query.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load projects"
            description={
              query.error instanceof ApiError
                ? query.error.message
                : "Something went wrong while loading projects."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void query.refetch()}>
                Try again
              </Button>
            }
          />
        ) : query.isLoading ? (
          <EmptyContent
            fill
            icon={FolderKanban}
            title="Loading projects…"
            description="Fetching projects so you can open benchmarks."
          />
        ) : (query.data?.items.length ?? 0) === 0 ? (
          <EmptyContent
            fill
            icon={FlaskConical}
            title="No projects yet"
            description="Create a project, seed Coding Benchmark v1, then return here."
            action={
              <Button asChild>
                <Link href="/projects">Go to projects</Link>
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-border">
            {(query.data?.items ?? []).map((project) => (
              <li key={project.id} className="flex items-center justify-between gap-4 py-3">
                <div>
                  <Text as="div" variant="body" className="font-medium">
                    {project.name}
                  </Text>
                  <Text as="div" variant="caption">
                    {project.id}
                  </Text>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/projects/${project.id}/benchmarks`}>Open benchmarks</Link>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </PageLayout>
  );
}
