"use client";

import {
  Button,
  DataGrid,
  DataGridPagination,
  DataGridSearch,
  FlaskConical,
  Plus,
} from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { caseColumns } from "./columns";
import { CreateCaseDialog } from "./create-case-dialog";
import { casesQueryKey } from "./utils";

import type { PaginationState, SortingState } from "@tanstack/react-table";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { projectQueryKey } from "@/features/projects/utils";
import { listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function CaseListPage({
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

  const casesQuery = useQuery({
    queryKey: [...casesQueryKey(projectId), "list"],
    enabled: Boolean(token) && projectQuery.isSuccess,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listCases(token, {
        project_id: projectId,
        limit: 100,
        sort: "-created_at",
      });
    },
  });

  const cases = useMemo(() => casesQuery.data?.items ?? [], [casesQuery.data]);
  const pageCount = Math.max(1, Math.ceil(cases.length / pagination.pageSize) || 1);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    if (!open && initialCreateOpen) {
      router.replace(`/projects/${projectId}/cases`);
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
        eyebrow="Cases"
        title="Cases"
        description={`Evaluation cases for ${project.name}. Each case owns prompt versions and versioned task definitions.`}
        actions={
          <Button
            type="button"
            leftIcon={Plus}
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New case
          </Button>
        }
      />

      <Section className="mt-8">
        {casesQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load cases"
            description={
              casesQuery.error instanceof ApiError
                ? casesQuery.error.message
                : "Something went wrong while loading cases."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void casesQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={caseColumns}
            data={cases}
            getRowId={(row) => row.id}
            loading={casesQuery.isLoading}
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
            emptyTitle={globalFilter.trim() ? "No matching cases" : "Add your first case"}
            emptyDescription={
              globalFilter.trim()
                ? "Try a different search, or clear the filter to see all cases."
                : "Define a task and prompt, then publish a case version to use in suites and runs."
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
                  Create case
                </Button>
              )
            }
            onRowActivate={(row) => {
              router.push(`/projects/${projectId}/cases/${row.original.id}`);
            }}
            aria-label="Cases"
            toolbar={
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <DataGridSearch
                  value={globalFilter}
                  onValueChange={(value) => {
                    setGlobalFilter(value);
                    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                  }}
                  placeholder="Search cases…"
                  className="max-w-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  leftIcon={FlaskConical}
                  onClick={() => {
                    setCreateOpen(true);
                  }}
                >
                  New case
                </Button>
              </div>
            }
            footer={
              cases.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={cases.length}
                />
              ) : null
            }
          />
        )}
      </Section>

      <CreateCaseDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        projectId={projectId}
        onCreated={(caseId) => {
          router.push(`/projects/${projectId}/cases/${caseId}`);
        }}
      />
    </PageLayout>
  );
}
