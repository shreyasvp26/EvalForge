"use client";

import { Button, FolderKanban, Text } from "@agent-eval/ui";
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

/**
 * Global /cases entry: cases are project-scoped, so guide the user into a project.
 */
export function CasesIndexPage() {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: [...projectsQueryKey, "list", "cases-index"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProjects(token, { limit: 100, sort: "-created_at" });
    },
  });

  return (
    <PageLayout>
      <PageHeader
        eyebrow="Workspace"
        title="Cases"
        description="Cases live inside a project. Choose a project to open its cases list."
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
            description="Fetching projects so you can open cases."
          />
        ) : (query.data?.items.length ?? 0) === 0 ? (
          <EmptyContent
            fill
            icon={FolderKanban}
            title="No projects yet"
            description="Create a project first, then add cases under that project."
            action={
              <Button asChild>
                <Link href="/projects?create=1">Create project</Link>
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
            {query.data?.items.map((project) => (
              <li key={project.id}>
                <Link
                  href={`/projects/${project.id}/cases`}
                  className="flex flex-col gap-1 px-4 py-3 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <Text as="div" variant="body" className="font-medium">
                      {project.name}
                    </Text>
                    <Text as="div" variant="caption" className="line-clamp-1">
                      {project.description.trim() || "No description"}
                    </Text>
                  </div>
                  <Text as="span" variant="caption" className="shrink-0 text-accent">
                    Open cases →
                  </Text>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </PageLayout>
  );
}
