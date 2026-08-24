"use client";

import { ArrowRight, Button, FadeIn, Text } from "@agent-eval/ui";
import Link from "next/link";

import { ActiveExecution, RecentFailures } from "./active-execution";
import { DashboardEmpty } from "./dashboard-empty";
import { EvaluationHealthStrip } from "./evaluation-health";
import { useDashboardData } from "./hooks";
import { QuickActions } from "./quick-actions";
import { RecentEvaluations } from "./recent-evaluations";
import { RecentResults } from "./recent-results";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
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
            eyebrow="Evaluation control plane"
            title="Evaluation overview"
            description="Operational snapshot of recent evaluations across sampled projects."
          />
          <div className="mt-8">
            <DashboardEmpty />
          </div>
        </FadeIn>
      </PageLayout>
    );
  }

  return (
    <PageLayout width="full" className="max-w-6xl">
      <FadeIn>
        <PageHeader
          eyebrow="Evaluation control plane"
          title="Evaluation overview"
          description="Operational snapshot of recent evaluations across sampled projects."
          actions={
            <Button asChild size="lg" rightIcon={ArrowRight}>
              <Link href="/runs/new">Launch evaluation</Link>
            </Button>
          }
        />

        <div className="mt-8 space-y-8">
          <EvaluationHealthStrip health={snapshot.health} />

          <div className="grid gap-8 lg:grid-cols-3">
            <Section
              title="Active execution"
              description="Queued, running, and grading right now."
              className="lg:col-span-1"
            >
              <ActiveExecution
                runs={snapshot.activeRuns}
                projectNameById={snapshot.projectNameById}
              />
            </Section>

            <Section
              title="Needs attention"
              description="Failed runs and completed runs with failing scores."
              className="lg:col-span-2"
            >
              <RecentFailures runs={snapshot.failures} projectNameById={snapshot.projectNameById} />
            </Section>

            <Section
              title="Recent evaluations"
              className="lg:col-span-2"
              description="Latest runs across sampled projects."
              actions={
                <Button asChild variant="ghost" size="sm">
                  <Link href="/runs">View all</Link>
                </Button>
              }
            >
              <RecentEvaluations
                runs={snapshot.activity}
                projectNameById={snapshot.projectNameById}
              />
            </Section>

            <Section title="Workflow" description="Start or configure the evaluation model.">
              <QuickActions />
            </Section>

            <Section
              title="Recent scores"
              className="lg:col-span-3"
              description="Grader outcomes attached to recent runs."
            >
              <RecentResults results={snapshot.results} />
            </Section>
          </div>

          <Text variant="caption" className="block text-muted-foreground">
            Health and feeds sample up to eight recent projects — open Projects or Runs for the full
            inventory.
          </Text>
        </div>
      </FadeIn>
    </PageLayout>
  );
}
