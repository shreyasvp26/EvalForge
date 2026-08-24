"use client";

import { Button, DataGrid, DataGridPagination, DataGridSearch, Plus } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { agentColumns } from "./columns";
import { CreateAgentDialog } from "./create-agent-dialog";
import { agentsQueryKey } from "./utils";

import type { PaginationState, SortingState } from "@tanstack/react-table";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { listAgents } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export function AgentListPage({ initialCreateOpen = false }: { initialCreateOpen?: boolean }) {
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

  const agentsQuery = useQuery({
    queryKey: [...agentsQueryKey, "list"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listAgents(token, { limit: 100, sort: "-created_at" });
    },
  });

  const agents = useMemo(() => agentsQuery.data?.items ?? [], [agentsQuery.data]);
  const pageCount = Math.max(1, Math.ceil(agents.length / pagination.pageSize) || 1);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    if (!open && initialCreateOpen) {
      router.replace("/agents");
    }
  }

  return (
    <PageLayout width="full">
      <PageHeader
        eyebrow="Platform"
        title="Agents"
        description="Adapters that execute evaluations."
        actions={
          <Button
            type="button"
            leftIcon={Plus}
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New agent
          </Button>
        }
      />

      <Section className="mt-8">
        {agentsQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load agents"
            description={
              agentsQuery.error instanceof ApiError
                ? agentsQuery.error.message
                : "Something went wrong while loading agents."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void agentsQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={agentColumns}
            data={agents}
            getRowId={(row) => row.id}
            loading={agentsQuery.isLoading}
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
            emptyTitle={globalFilter.trim() ? "No matching agents" : "Register an agent"}
            emptyDescription={
              globalFilter.trim()
                ? "Try a different search, or clear the filter."
                : "Connect an adapter, publish a version, then pin it when you launch evaluations."
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
                  New agent
                </Button>
              )
            }
            onRowActivate={(row) => {
              router.push(`/agents/${row.original.id}`);
            }}
            aria-label="Agents"
            toolbar={
              <DataGridSearch
                value={globalFilter}
                onValueChange={(value) => {
                  setGlobalFilter(value);
                  setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                }}
                placeholder="Search agents…"
                className="max-w-sm"
              />
            }
            footer={
              agents.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={agents.length}
                />
              ) : null
            }
          />
        )}
      </Section>

      <CreateAgentDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        onCreated={(agentId) => {
          router.push(`/agents/${agentId}`);
        }}
      />
    </PageLayout>
  );
}
