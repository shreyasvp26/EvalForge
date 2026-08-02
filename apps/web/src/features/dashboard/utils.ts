import type { Agent } from "@/lib/api/agents";
import type { Case } from "@/lib/api/cases";
import type { Grader } from "@/lib/api/graders";
import type { Project } from "@/lib/api/projects";
import type { Run, Score } from "@/lib/api/runs";
import type { Suite } from "@/lib/api/suites";

import {
  formatScoreValue,
  runStatusBadge,
  runStatusLabel,
  truncateId,
} from "@/features/runs/utils";

export { formatScoreValue, runStatusBadge, runStatusLabel, truncateId };

export const dashboardQueryKey = ["dashboard"] as const;

export const DASHBOARD_PROJECT_FANOUT = 8;
export const DASHBOARD_LIST_LIMIT = 8;
export const DASHBOARD_ACTIVITY_LIMIT = 12;
export const DASHBOARD_RESULTS_LIMIT = 10;

export function formatDashboardDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatCount(count: number, hasMore: boolean): string {
  if (hasMore) return `${String(count)}+`;
  return String(count);
}

/** Latest activity timestamp for suites/cases (entity or newest version). */
export function latestResourceAt(resource: {
  created_at: string;
  versions?: { created_at: string }[];
}): string {
  let latest = resource.created_at;
  for (const version of resource.versions ?? []) {
    if (new Date(version.created_at).getTime() > new Date(latest).getTime()) {
      latest = version.created_at;
    }
  }
  return latest;
}

export function sortByDateDesc<T>(items: T[], getDate: (item: T) => string): T[] {
  return [...items].sort((a, b) => new Date(getDate(b)).getTime() - new Date(getDate(a)).getTime());
}

export type ScoreOutcome = "passed" | "failed" | "partial";

export function scoreOutcome(score: Score, run: Run): ScoreOutcome {
  if (score.value.passed === true) return "passed";
  if (score.value.passed === false) return "failed";
  if (run.is_partially_graded) return "partial";
  if (score.value.numeric !== null || score.value.categorical) return "partial";
  return "partial";
}

export function scoreOutcomeBadge(outcome: ScoreOutcome): "completed" | "danger" | "warning" {
  if (outcome === "passed") return "completed";
  if (outcome === "failed") return "danger";
  return "warning";
}

export function scoreOutcomeLabel(outcome: ScoreOutcome): string {
  if (outcome === "passed") return "Passed";
  if (outcome === "failed") return "Failed";
  return "Partial";
}

export interface DashboardSummary {
  projects: number;
  projectsHasMore: boolean;
  suites: number;
  cases: number;
  agents: number;
  agentsHasMore: boolean;
  graders: number;
  gradersHasMore: boolean;
  runs: number;
}

export interface DashboardScoreRow {
  score: Score;
  run: Run;
  projectName: string;
  outcome: ScoreOutcome;
}

export interface DashboardSnapshot {
  projects: Project[];
  projectsHasMore: boolean;
  agents: Agent[];
  agentsHasMore: boolean;
  graders: Grader[];
  gradersHasMore: boolean;
  suites: Suite[];
  cases: Case[];
  runs: Run[];
  summary: DashboardSummary;
  activity: Run[];
  results: DashboardScoreRow[];
  projectNameById: Record<string, string>;
  isEmpty: boolean;
}

export function buildDashboardSnapshot(input: {
  projects: Project[];
  projectsHasMore: boolean;
  agents: Agent[];
  agentsHasMore: boolean;
  graders: Grader[];
  gradersHasMore: boolean;
  suites: Suite[];
  cases: Case[];
  runs: Run[];
}): DashboardSnapshot {
  const projectNameById = Object.fromEntries(
    input.projects.map((project) => [project.id, project.name]),
  );

  const runs = sortByDateDesc(input.runs, (run) => run.created_at);
  const suites = sortByDateDesc(input.suites, latestResourceAt);
  const cases = sortByDateDesc(input.cases, latestResourceAt);
  const agents = sortByDateDesc(
    input.agents.filter((agent) => agent.status !== "deprecated"),
    (agent) => agent.created_at,
  );

  const results: DashboardScoreRow[] = [];
  for (const run of runs) {
    for (const score of run.scores) {
      results.push({
        score,
        run,
        projectName: projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10),
        outcome: scoreOutcome(score, run),
      });
    }
  }

  const summary: DashboardSummary = {
    projects: input.projects.length,
    projectsHasMore: input.projectsHasMore,
    suites: input.suites.length,
    cases: input.cases.length,
    agents: input.agents.length,
    agentsHasMore: input.agentsHasMore,
    graders: input.graders.length,
    gradersHasMore: input.gradersHasMore,
    runs: input.runs.length,
  };

  const isEmpty =
    input.projects.length === 0 &&
    input.agents.length === 0 &&
    input.graders.length === 0 &&
    input.runs.length === 0;

  return {
    projects: input.projects,
    projectsHasMore: input.projectsHasMore,
    agents,
    agentsHasMore: input.agentsHasMore,
    graders: input.graders,
    gradersHasMore: input.gradersHasMore,
    suites,
    cases,
    runs,
    summary,
    activity: runs.slice(0, DASHBOARD_ACTIVITY_LIMIT),
    results: results.slice(0, DASHBOARD_RESULTS_LIMIT),
    projectNameById,
    isEmpty,
  };
}
