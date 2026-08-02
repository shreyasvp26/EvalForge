"use client";

import { useQuery } from "@tanstack/react-query";

import { DASHBOARD_PROJECT_FANOUT, buildDashboardSnapshot, dashboardQueryKey } from "../utils";

import type { Case } from "@/lib/api/cases";
import type { Run } from "@/lib/api/runs";
import type { Suite } from "@/lib/api/suites";

import { listAgents } from "@/lib/api/agents";
import { listCases } from "@/lib/api/cases";
import { listGraders } from "@/lib/api/graders";
import { listProjects } from "@/lib/api/projects";
import { listRuns } from "@/lib/api/runs";
import { listSuites } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

/**
 * Composes dashboard data from existing list endpoints.
 * Project-scoped resources (suites/cases/runs) are fan-out queried for the
 * most recent projects — there is no cross-project aggregation API yet.
 */
export function useDashboardData() {
  const { token } = useAuth();

  return useQuery({
    queryKey: [...dashboardQueryKey, "snapshot"],
    enabled: Boolean(token),
    staleTime: 15_000,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");

      const [projectsRes, agentsRes, gradersRes] = await Promise.all([
        listProjects(token, { limit: 50, sort: "-created_at" }),
        listAgents(token, { limit: 50, sort: "-created_at" }),
        listGraders(token, { limit: 50, sort: "-created_at" }),
      ]);

      const fanoutProjects = projectsRes.items.slice(0, DASHBOARD_PROJECT_FANOUT);

      const scoped = await Promise.all(
        fanoutProjects.map(async (project) => {
          const [suitesRes, casesRes, runsRes] = await Promise.all([
            listSuites(token, {
              project_id: project.id,
              limit: 20,
              sort: "-created_at",
            }),
            listCases(token, {
              project_id: project.id,
              limit: 20,
              sort: "-created_at",
            }),
            listRuns(token, {
              project_id: project.id,
              limit: 20,
              sort: "-created_at",
            }),
          ]);
          return {
            suites: suitesRes.items,
            cases: casesRes.items,
            runs: runsRes.items,
          };
        }),
      );

      const suites: Suite[] = [];
      const cases: Case[] = [];
      const runs: Run[] = [];
      for (const chunk of scoped) {
        suites.push(...chunk.suites);
        cases.push(...chunk.cases);
        runs.push(...chunk.runs);
      }

      return buildDashboardSnapshot({
        projects: projectsRes.items,
        projectsHasMore: projectsRes.has_more,
        agents: agentsRes.items,
        agentsHasMore: agentsRes.has_more,
        graders: gradersRes.items,
        gradersHasMore: gradersRes.has_more,
        suites,
        cases,
        runs,
      });
    },
  });
}
