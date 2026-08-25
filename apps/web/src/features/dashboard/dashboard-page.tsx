"use client";

import { Button, FadeIn, Icon, Play, Text } from "@agent-eval/ui";
import Link from "next/link";

import { ActiveExecution, RecentFailures } from "./active-execution";
import { DashboardEmpty } from "./dashboard-empty";
import { EvaluationHealthStrip } from "./evaluation-health";
import { useDashboardData } from "./hooks";
import { QuickActions } from "./quick-actions";
import { RecentEvaluations } from "./recent-evaluations";

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
      <PageLayout width="full" className="max-w-7xl">
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (query.isError) {
    return (
      <PageLayout width="full" className="max-w-7xl">
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
      <PageLayout width="full" className="max-w-7xl">
        <FadeIn>
          <PageHeader
            eyebrow="Workspace"
            title="Overview"
            description="Here's what's happening with your evaluations."
            actions={
              <Button
                asChild
                size="lg"
                className="ef-auth-primary-fill border-0 hover:bg-transparent"
              >
                <Link href="/runs/new" className="inline-flex items-center gap-2">
                  <Icon icon={Play} size="sm" aria-hidden />
                  Launch run
                </Link>
              </Button>
            }
          />
          <div className="mt-8">
            <DashboardEmpty />
          </div>
        </FadeIn>
      </PageLayout>
    );
  }

  return (
    <PageLayout width="full" className="max-w-7xl">
      <FadeIn>
        <PageHeader
          eyebrow="Workspace"
          title="Overview"
          description="Here's what's happening with your evaluations."
          actions={
            <Button
              asChild
              size="lg"
              className="ef-auth-primary-fill border-0 shadow-[0_4px_24px_var(--ef-auth-primary-glow)] hover:bg-transparent"
            >
              <Link href="/runs/new" className="inline-flex items-center gap-2">
                <Icon icon={Play} size="sm" aria-hidden />
                Launch run
              </Link>
            </Button>
          }
        />

        <div className="mt-8 space-y-8">
          <EvaluationHealthStrip health={snapshot.health} />

          <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
            <Section
              title="Recent evaluations"
              className="lg:col-span-2"
              description="Latest runs across sampled projects."
              actions={
                <Button asChild variant="ghost" size="sm" className="text-[var(--ef-accent)]">
                  <Link href="/runs">View all</Link>
                </Button>
              }
            >
              <RecentEvaluations
                runs={snapshot.activity}
                projectNameById={snapshot.projectNameById}
              />
            </Section>

            <div className="space-y-6">
              <Section
                title="Active executions"
                description="Queued, running, and grading right now."
              >
                <ActiveExecution
                  runs={snapshot.activeRuns}
                  projectNameById={snapshot.projectNameById}
                />
              </Section>

              <Section
                title="Recent failures"
                description="Failed runs and failing scores."
                actions={
                  <Button asChild variant="ghost" size="sm" className="text-[var(--ef-accent)]">
                    <Link href="/runs">View all</Link>
                  </Button>
                }
              >
                <RecentFailures
                  runs={snapshot.failures}
                  projectNameById={snapshot.projectNameById}
                />
              </Section>
            </div>
          </div>

          <Section title="Quick actions" description="What should you do next?">
            <QuickActions />
          </Section>

          <Text variant="caption" className="block text-muted-foreground">
            Health and feeds sample up to eight recent projects — open Projects or Runs for the full
            inventory.
          </Text>
        </div>
      </FadeIn>
    </PageLayout>
  );
}
