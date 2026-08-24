"use client";

import {
  Button,
  DataGrid,
  DataGridPagination,
  DataGridSearch,
  Play,
  Plus,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Text,
} from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { CancelRunDialog } from "./cancel-run-dialog";
import { createRunColumns } from "./columns";
import {
  RUN_STATUS_FILTERS,
  pinsSummary,
  runStatusLabel,
  runsListQueryKey,
  truncateId,
} from "./utils";

import type { Run } from "@/lib/api/runs";
import type { PaginationState, SortingState } from "@tanstack/react-table";

import { EmptyContent } from "@/components/layouts/empty-content";
import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { agentsQueryKey } from "@/features/agents/utils";
import { casesQueryKey } from "@/features/cases/utils";
import { projectsQueryKey } from "@/features/projects/utils";
import { listAgents } from "@/lib/api/agents";
import { listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { listProjects } from "@/lib/api/projects";
import { listRuns } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function RunListPage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectFromUrl = searchParams.get("project") ?? "";
  const statusFromUrl = searchParams.get("status") ?? "";

  const [projectId, setProjectId] = useState(projectFromUrl);
  const [statusFilter, setStatusFilter] = useState(statusFromUrl);
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 20,
  });
  const [cancelTarget, setCancelTarget] = useState<Run | null>(null);

  const projectsQuery = useQuery({
    queryKey: [...projectsQueryKey, "list", "runs"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProjects(token, { limit: 100, sort: "-created_at" });
    },
  });

  const effectiveProjectId =
    projectId ||
    (projectsQuery.data?.items.length === 1 ? (projectsQuery.data.items[0]?.id ?? "") : "");

  const runsQuery = useQuery({
    queryKey: [...runsListQueryKey(effectiveProjectId), statusFilter || "all"],
    enabled: Boolean(token) && Boolean(effectiveProjectId),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRuns(token, {
        project_id: effectiveProjectId,
        limit: 100,
        sort: "-created_at",
        ...(statusFilter ? { status: statusFilter } : {}),
      });
    },
  });

  const casesQuery = useQuery({
    queryKey: [...casesQueryKey(effectiveProjectId), "list", "runs-resolve"],
    enabled: Boolean(token) && Boolean(effectiveProjectId),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listCases(token, { project_id: effectiveProjectId, limit: 100 });
    },
  });

  const agentsQuery = useQuery({
    queryKey: [...agentsQueryKey, "list", "runs-resolve"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listAgents(token, { limit: 100 });
    },
  });

  const projectName =
    projectsQuery.data?.items.find((project) => project.id === effectiveProjectId)?.name ??
    "Project";

  const caseLabelByVersion = useMemo(() => {
    const map = new Map<string, string>();
    for (const caseItem of casesQuery.data?.items ?? []) {
      for (const version of caseItem.versions) {
        map.set(version.id, `${caseItem.name} · v${String(version.version_number)}`);
      }
    }
    return map;
  }, [casesQuery.data]);

  const agentLabelByVersion = useMemo(() => {
    const map = new Map<string, string>();
    for (const agent of agentsQuery.data?.items ?? []) {
      for (const version of agent.versions) {
        map.set(version.id, `${agent.name} · v${String(version.version_number)}`);
      }
    }
    return map;
  }, [agentsQuery.data]);

  const runs = useMemo(() => {
    const items = runsQuery.data?.items ?? [];
    const query = globalFilter.trim().toLowerCase();
    if (!query) return items;
    return items.filter((run) => {
      const haystack = [
        run.id,
        run.status,
        pinsSummary(run),
        caseLabelByVersion.get(run.pins.case_version_id) ?? "",
        agentLabelByVersion.get(run.pins.agent_version_id) ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [runsQuery.data, globalFilter, caseLabelByVersion, agentLabelByVersion]);

  const pageCount = Math.max(1, Math.ceil(runs.length / pagination.pageSize) || 1);

  const columns = useMemo(
    () =>
      createRunColumns({
        projectName,
        resolveCaseLabel: (caseVersionId) =>
          caseLabelByVersion.get(caseVersionId) ?? truncateId(caseVersionId),
        resolveAgentLabel: (agentVersionId) =>
          agentLabelByVersion.get(agentVersionId) ?? truncateId(agentVersionId),
        onCancel: (run) => {
          setCancelTarget(run);
        },
      }),
    [projectName, caseLabelByVersion, agentLabelByVersion],
  );

  function updateFilters(nextProject: string, nextStatus: string) {
    setProjectId(nextProject);
    setStatusFilter(nextStatus);
    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
    const params = new URLSearchParams();
    if (nextProject) params.set("project", nextProject);
    if (nextStatus) params.set("status", nextStatus);
    const query = params.toString();
    router.replace(query ? `/runs?${query}` : "/runs");
  }

  return (
    <PageLayout width="full">
      <PageHeader
        eyebrow="Evaluation"
        title="Runs"
        description="Pinned evaluation executions. Status, score, and context at a glance."
        actions={
          <Button asChild leftIcon={Plus}>
            <Link href="/runs/new">Launch run</Link>
          </Button>
        }
      />

      <Section className="mt-8">
        {projectsQuery.isError ? (
          <ErrorContent
            fill
            title="Couldn’t load projects"
            description={
              projectsQuery.error instanceof ApiError
                ? projectsQuery.error.message
                : "Something went wrong while loading projects."
            }
            action={
              <Button type="button" variant="outline" onClick={() => void projectsQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (projectsQuery.data?.items.length ?? 0) === 0 && !projectsQuery.isLoading ? (
          <EmptyContent
            fill
            icon={Play}
            title="Create a project to continue"
            description="Projects hold cases and suites. Create one, then launch evaluations from Runs."
            action={
              <Button asChild>
                <Link href="/projects?create=1">Create project</Link>
              </Button>
            }
          />
        ) : (
          <DataGrid
            columns={columns}
            data={runs}
            getRowId={(row) => row.id}
            loading={Boolean(effectiveProjectId) && runsQuery.isLoading}
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
            emptyTitle={
              !effectiveProjectId
                ? "Select a project"
                : globalFilter.trim()
                  ? "No matching runs"
                  : "No evaluations yet"
            }
            emptyDescription={
              !effectiveProjectId
                ? "Choose a project to load its evaluation runs."
                : globalFilter.trim()
                  ? "Try a different search, or clear the filter."
                  : "Pin a case, agent, and grader, then launch your first evaluation."
            }
            emptyAction={
              effectiveProjectId && !globalFilter.trim() ? (
                <Button asChild leftIcon={Plus}>
                  <Link href={`/runs/new?project=${encodeURIComponent(effectiveProjectId)}`}>
                    Create evaluation
                  </Link>
                </Button>
              ) : undefined
            }
            onRowActivate={(row) => {
              router.push(`/runs/${row.original.id}`);
            }}
            aria-label="Runs"
            toolbar={
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <DataGridSearch
                    value={globalFilter}
                    onValueChange={(value) => {
                      setGlobalFilter(value);
                      setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                    }}
                    placeholder="Search runs…"
                    className="max-w-sm"
                  />
                  <Select
                    {...(effectiveProjectId ? { value: effectiveProjectId } : {})}
                    onValueChange={(value) => {
                      updateFilters(value, statusFilter);
                    }}
                    disabled={projectsQuery.isLoading}
                  >
                    <SelectTrigger className="w-full sm:w-56" aria-label="Filter by project">
                      <SelectValue placeholder="Select project" />
                    </SelectTrigger>
                    <SelectContent>
                      {projectsQuery.data?.items.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={statusFilter || "all"}
                    onValueChange={(value) => {
                      updateFilters(effectiveProjectId, value === "all" ? "" : value);
                    }}
                  >
                    <SelectTrigger className="w-full sm:w-44" aria-label="Filter by status">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      {RUN_STATUS_FILTERS.map((item) => (
                        <SelectItem key={item.value || "all"} value={item.value || "all"}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Text variant="caption" className="shrink-0">
                  {effectiveProjectId
                    ? `${String(runs.length)} run${runs.length === 1 ? "" : "s"}`
                    : "Project required"}
                </Text>
              </div>
            }
            footer={
              runs.length > 0 ? (
                <DataGridPagination
                  pagination={pagination}
                  onPaginationChange={setPagination}
                  pageCount={pageCount}
                  totalRows={runs.length}
                />
              ) : null
            }
          />
        )}

        {runsQuery.isError && effectiveProjectId ? (
          <div className="mt-4">
            <ErrorContent
              title="Couldn’t load runs"
              description={
                runsQuery.error instanceof ApiError
                  ? runsQuery.error.message
                  : "Something went wrong while loading runs."
              }
              action={
                <Button type="button" variant="outline" onClick={() => void runsQuery.refetch()}>
                  Try again
                </Button>
              }
            />
          </div>
        ) : null}
      </Section>

      <CancelRunDialog
        open={cancelTarget !== null}
        onOpenChange={(open) => {
          if (!open) setCancelTarget(null);
        }}
        runId={cancelTarget?.id ?? ""}
        projectId={cancelTarget?.pins.project_id ?? effectiveProjectId}
        statusLabel={cancelTarget ? runStatusLabel(cancelTarget.status) : ""}
      />
    </PageLayout>
  );
}
