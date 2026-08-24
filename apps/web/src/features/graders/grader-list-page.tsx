"use client";

import { Button, DataGrid, DataGridPagination, DataGridSearch, Plus } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { graderColumns } from "./columns";
import { CreateGraderDialog } from "./create-grader-dialog";
import { gradersQueryKey } from "./utils";

import type { PaginationState, SortingState } from "@tanstack/react-table";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { ApiError } from "@/lib/api/client";
import { listGraders } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

export function GraderListPage({ initialCreateOpen = false }: { initialCreateOpen?: boolean }) {
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

  const gradersQuery = useQuery({
    queryKey: [...gradersQueryKey, "list"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGraders(token, { limit: 100, sort: "-created_at" });
    },
  });

  const graders = useMemo(() => gradersQuery.data?.items ?? [], [gradersQuery.data]);
  const pageCount = Math.max(1, Math.ceil(graders.length / pagination.pageSize) || 1);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    if (!open && initialCreateOpen) {
      router.replace("/graders");
    }
  }

  return (
    <PageLayout width="full">
      <PageHeader
        eyebrow="Platform"
        title="Graders"
        description="Objective scoring for runs."
        actions={
          <Button
            type="button"
            leftIcon={Plus}
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New grader
          </Button>
        }
      />

      <Section className="mt-8">
        {gradersQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load graders"
            description={
              gradersQuery.error instanceof ApiError
                ? gradersQuery.error.message
                : "Something went wrong while loading graders."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void gradersQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={graderColumns}
            data={graders}
            getRowId={(row) => row.id}
            loading={gradersQuery.isLoading}
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
            emptyTitle={globalFilter.trim() ? "No matching graders" : "Register a grader"}
            emptyDescription={
              globalFilter.trim()
                ? "Try a different search, or clear the filter."
                : "Publish a specification, then pin the grader version on evaluation runs."
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
                  New grader
                </Button>
              )
            }
            onRowActivate={(row) => {
              router.push(`/graders/${row.original.id}`);
            }}
            aria-label="Graders"
            toolbar={
              <DataGridSearch
                value={globalFilter}
                onValueChange={(value) => {
                  setGlobalFilter(value);
                  setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                }}
                placeholder="Search graders…"
                className="max-w-sm"
              />
            }
            footer={
              graders.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={graders.length}
                />
              ) : null
            }
          />
        )}
      </Section>

      <CreateGraderDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        onCreated={(graderId) => {
          router.push(`/graders/${graderId}`);
        }}
      />
    </PageLayout>
  );
}
