"use client";

import { Button, DataGrid, DataGridPagination, DataGridSearch, Layers, Plus } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { suiteColumns } from "./columns";
import { CreateSuiteDialog } from "./create-suite-dialog";
import { suitesQueryKey } from "./utils";

import type { PaginationState, SortingState } from "@tanstack/react-table";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { projectQueryKey } from "@/features/projects/utils";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { listSuites } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

export function SuiteListPage({
  projectId,
  initialCreateOpen = false,
}: {
  projectId: string;
  initialCreateOpen?: boolean;
}) {
  const { token } = useAuth();
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(initialCreateOpen);
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 20,
  });

  useEffect(() => {
    if (initialCreateOpen) setCreateOpen(true);
  }, [initialCreateOpen]);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const suitesQuery = useQuery({
    queryKey: [...suitesQueryKey(projectId), "list"],
    enabled: Boolean(token) && projectQuery.isSuccess,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listSuites(token, {
        project_id: projectId,
        limit: 100,
        sort: "-created_at",
      });
    },
  });

  const suites = useMemo(() => suitesQuery.data?.items ?? [], [suitesQuery.data]);
  const pageCount = Math.max(1, Math.ceil(suites.length / pagination.pageSize) || 1);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    if (!open && initialCreateOpen) {
      router.replace(`/projects/${projectId}/suites`);
    }
  }

  if (projectQuery.isLoading) {
    return (
      <PageLayout width="full">
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (projectQuery.isError) {
    const error = projectQuery.error;
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
          description={error instanceof ApiError ? error.message : "Something went wrong."}
          action={
            <Button type="button" variant="outline" onClick={() => void projectQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const project = projectQuery.data;
  if (!project) return null;

  return (
    <PageLayout width="full">
      <PageHeader
        eyebrow="Suites"
        title="Suites"
        description={`Evaluation suites for ${project.name}. Each suite versions an ordered composition of case versions.`}
        actions={
          <Button
            type="button"
            leftIcon={Plus}
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New suite
          </Button>
        }
      />

      <Section className="mt-8">
        {suitesQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load suites"
            description={
              suitesQuery.error instanceof ApiError
                ? suitesQuery.error.message
                : "Something went wrong while loading suites."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void suitesQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={suiteColumns}
            data={suites}
            getRowId={(row) => row.id}
            loading={suitesQuery.isLoading}
            loadingRowCount={6}
            sorting={sorting}
            onSortingChange={setSorting}
            globalFilter={globalFilter}
            onGlobalFilterChange={(value) => {
              setGlobalFilter(value);
              setPagination((prev) => ({ ...prev, pageIndex: 0 }));
            }}
            pagination={pagination}
            onPaginationChange={setPagination}
            emptyTitle={globalFilter.trim() ? "No matching suites" : "Compose your first suite"}
            emptyDescription={
              globalFilter.trim()
                ? "Try a different search, or clear the filter to see all suites."
                : "Group published case versions in order so runs can evaluate a full set."
            }
            emptyAction={
              globalFilter.trim() ? undefined : (
                <Button
                  type="button"
                  leftIcon={Plus}
                  onClick={() => {
                    setCreateOpen(true);
                  }}
                >
                  Create suite
                </Button>
              )
            }
            onRowActivate={(row) => {
              router.push(`/projects/${projectId}/suites/${row.original.id}`);
            }}
            aria-label="Suites"
            toolbar={
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <DataGridSearch
                  value={globalFilter}
                  onValueChange={(value) => {
                    setGlobalFilter(value);
                    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                  }}
                  placeholder="Search suites…"
                  className="max-w-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  leftIcon={Layers}
                  onClick={() => {
                    setCreateOpen(true);
                  }}
                >
                  New suite
                </Button>
              </div>
            }
            footer={
              suites.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={suites.length}
                />
              ) : null
            }
          />
        )}
      </Section>

      <CreateSuiteDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        projectId={projectId}
        onCreated={(suiteId) => {
          router.push(`/projects/${projectId}/suites/${suiteId}`);
        }}
      />
    </PageLayout>
  );
}
