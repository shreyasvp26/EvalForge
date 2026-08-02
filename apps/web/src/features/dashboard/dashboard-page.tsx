"use client";

import { Button, FadeIn, Text } from "@agent-eval/ui";
import Link from "next/link";

import { DashboardEmpty } from "./dashboard-empty";
import { useDashboardData } from "./hooks";
import { PlatformSummary } from "./platform-summary";
import { QuickActions } from "./quick-actions";
import { RecentResults } from "./recent-results";
import { ResourceList } from "./resource-list";
import { RunActivity } from "./run-activity";
import { DASHBOARD_LIST_LIMIT, latestResourceAt, truncateId } from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { entityStatusLabel as agentStatusLabel } from "@/features/agents/utils";
import { projectStatusLabel } from "@/features/projects/utils";
import { ApiError } from "@/lib/api/client";

export function DashboardPage() {
  const query = useDashboardData();

  if (query.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (query.isError) {
    return (
      <PageLayout>
        <ErrorContent
          fill
          title="Couldn’t load overview"
          description={
            query.error instanceof ApiError
              ? query.error.message
              : "Something went wrong while loading the dashboard."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void query.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const snapshot = query.data;
  if (!snapshot) return null;

  if (snapshot.isEmpty) {
    return (
      <PageLayout>
        <FadeIn>
          <PageHeader
            breadcrumbs={
              <Breadcrumbs items={[{ label: "Workspace", href: "/" }, { label: "Overview" }]} />
            }
            eyebrow="Workspace"
            title="Overview"
            description="What is happening in your evaluation platform right now."
          />
          <div className="mt-8">
            <DashboardEmpty />
          </div>
        </FadeIn>
      </PageLayout>
    );
  }

  const recentProjects = snapshot.projects.slice(0, DASHBOARD_LIST_LIMIT).map((project) => ({
    id: project.id,
    title: project.name,
    meta: projectStatusLabel(project.status),
    href: `/projects/${project.id}`,
    timestamp: project.created_at,
  }));

  const recentRuns = snapshot.runs.slice(0, DASHBOARD_LIST_LIMIT).map((run) => ({
    id: run.id,
    title: truncateId(run.id, 14),
    meta: snapshot.projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10),
    href: `/runs/${run.id}`,
    timestamp: run.created_at,
  }));

  const activeAgents = snapshot.agents.slice(0, DASHBOARD_LIST_LIMIT).map((agent) => ({
    id: agent.id,
    title: agent.name,
    meta: agentStatusLabel(agent.status),
    href: `/agents/${agent.id}`,
    timestamp: agent.created_at,
  }));

  const recentSuites = snapshot.suites.slice(0, DASHBOARD_LIST_LIMIT).map((suite) => ({
    id: suite.id,
    title: suite.name,
    meta: snapshot.projectNameById[suite.project_id] ?? truncateId(suite.project_id, 10),
    href: `/projects/${suite.project_id}/suites/${suite.id}`,
    timestamp: latestResourceAt(suite),
  }));

  const recentCases = snapshot.cases.slice(0, DASHBOARD_LIST_LIMIT).map((item) => ({
    id: item.id,
    title: item.name,
    meta: snapshot.projectNameById[item.project_id] ?? truncateId(item.project_id, 10),
    href: `/projects/${item.project_id}/cases/${item.id}`,
    timestamp: latestResourceAt(item),
  }));

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          breadcrumbs={
            <Breadcrumbs items={[{ label: "Workspace", href: "/" }, { label: "Overview" }]} />
          }
          eyebrow="Workspace"
          title="Overview"
          description="What is happening in your evaluation platform right now."
        />

        <div className="mt-6">
          <PlatformSummary summary={snapshot.summary} />
          <Text variant="caption" className="mt-2 block">
            Counts sample recent projects for suites, cases, and runs. Open each area for the full
            list.
          </Text>
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          <Section
            title="Run activity"
            className="lg:col-span-2"
            description="Most recent runs across sampled projects."
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/runs">View all</Link>
              </Button>
            }
          >
            <RunActivity runs={snapshot.activity} projectNameById={snapshot.projectNameById} />
          </Section>

          <Section title="Quick actions">
            <QuickActions />
          </Section>

          <Section
            title="Recent results"
            className="lg:col-span-2"
            description="Latest grader scores from recent runs."
          >
            <RecentResults results={snapshot.results} />
          </Section>

          <Section
            title="Recent projects"
            description="Newest projects first."
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/projects">View all</Link>
              </Button>
            }
          >
            <ResourceList rows={recentProjects} emptyLabel="No projects yet." />
          </Section>

          <Section
            title="Recent runs"
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/runs">View all</Link>
              </Button>
            }
          >
            <ResourceList rows={recentRuns} emptyLabel="No runs yet." />
          </Section>

          <Section
            title="Active agents"
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/agents">View all</Link>
              </Button>
            }
          >
            <ResourceList rows={activeAgents} emptyLabel="No agents yet." />
          </Section>

          <Section
            title="Recently updated suites"
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/suites">View all</Link>
              </Button>
            }
          >
            <ResourceList rows={recentSuites} emptyLabel="No suites yet." />
          </Section>

          <Section
            title="Recently updated cases"
            className="lg:col-span-2"
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/cases">View all</Link>
              </Button>
            }
          >
            <ResourceList rows={recentCases} emptyLabel="No cases yet." />
          </Section>
        </div>
      </FadeIn>
    </PageLayout>
  );
}
