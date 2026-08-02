"use client";

import {
  Button,
  DataGrid,
  DataGridPagination,
  DataGridSearch,
  FolderKanban,
  Plus,
} from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { projectColumns } from "./columns";
import { CreateProjectDialog } from "./create-project-dialog";
import { projectsQueryKey } from "./utils";

import type { PaginationState, SortingState } from "@tanstack/react-table";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { ApiError } from "@/lib/api/client";
import { listProjects } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function ProjectListPage({ initialCreateOpen = false }: { initialCreateOpen?: boolean }) {
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
    if (initialCreateOpen) {
      setCreateOpen(true);
    }
  }, [initialCreateOpen]);

  const query = useQuery({
    queryKey: [...projectsQueryKey, "list"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProjects(token, { limit: 100, sort: "-created_at" });
    },
  });

  const projects = useMemo(() => query.data?.items ?? [], [query.data]);

  const pageCount = Math.max(1, Math.ceil(projects.length / pagination.pageSize) || 1);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    if (!open && initialCreateOpen) {
      router.replace("/projects");
    }
  }

  return (
    <PageLayout width="full">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/projects" }, { label: "Projects" }]} />
        }
        eyebrow="Workspace"
        title="Projects"
        description="Organize evaluation work into projects. Open a project to manage settings and related resources."
        actions={
          <Button
            type="button"
            leftIcon={Plus}
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New project
          </Button>
        }
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
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void query.refetch();
                }}
              >
                Try again
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={projectColumns}
            data={projects}
            getRowId={(row) => row.id}
            loading={query.isLoading}
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
            emptyTitle={globalFilter.trim() ? "No matching projects" : "No projects yet"}
            emptyDescription={
              globalFilter.trim()
                ? "Try a different search, or clear the filter to see all projects."
                : "Create your first project to start organizing suites, cases, and runs."
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
                  Create project
                </Button>
              )
            }
            onRowActivate={(row) => {
              router.push(`/projects/${row.original.id}`);
            }}
            aria-label="Projects"
            toolbar={
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <DataGridSearch
                  value={globalFilter}
                  onValueChange={(value) => {
                    setGlobalFilter(value);
                    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                  }}
                  placeholder="Search projects…"
                  className="max-w-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  leftIcon={FolderKanban}
                  onClick={() => {
                    setCreateOpen(true);
                  }}
                >
                  New project
                </Button>
              </div>
            }
            footer={
              projects.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={projects.length}
                />
              ) : null
            }
          />
        )}
      </Section>

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        onCreated={(projectId) => {
          router.push(`/projects/${projectId}`);
        }}
      />
    </PageLayout>
  );
}
