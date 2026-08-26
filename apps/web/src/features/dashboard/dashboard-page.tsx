"use client";

import { Button, Cluster, FadeIn, Icon, Play, Text } from "@agent-eval/ui";
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

const launchRunClassName =
  "ef-auth-primary-fill border-0 shadow-[0_2px_12px_var(--ef-auth-primary-glow)] hover:bg-transparent hover:brightness-110";

export function DashboardPage() {
  const query = useDashboardData();

  if (query.isLoading) {
    return (
      <PageLayout width="full">
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (query.isError) {
    return (
      <PageLayout width="full">
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
      <PageLayout width="full">
        <FadeIn>
          <PageHeader
            eyebrow="Workspace"
            title="Overview"
            description="Give a coding agent a real GitHub task, evaluate the result, and open a PR when it passes."
            className="space-y-2 [&_.flex]:gap-3"
            actions={
              <Button asChild size="md" className={launchRunClassName}>
                <Link href="/cases" className="inline-flex items-center gap-2">
                  <Icon icon={Play} size="sm" aria-hidden />
                  New task
                </Link>
              </Button>
            }
          />
          <div className="mt-5">
            <DashboardEmpty />
          </div>
        </FadeIn>
      </PageLayout>
    );
  }

  return (
    <PageLayout width="full">
      <FadeIn>
        <PageHeader
          eyebrow="Workspace"
          title="Overview"
          description="Give a coding agent a real GitHub task, evaluate the result, and open a PR when it passes."
          className="space-y-2 [&_.flex]:gap-3"
          actions={
            <Cluster gap={2}>
              <Button asChild size="md" variant="outline">
                <Link href="/runs/new">Launch run</Link>
              </Button>
              <Button asChild size="md" className={launchRunClassName}>
                <Link href="/cases" className="inline-flex items-center gap-2">
                  <Icon icon={Play} size="sm" aria-hidden />
                  New task
                </Link>
              </Button>
            </Cluster>
          }
        />

        <div className="mt-5 space-y-5">
          <EvaluationHealthStrip health={snapshot.health} />

          <Section
            title="Quick actions"
            description="Stay on the path from GitHub task to reviewable PR."
          >
            <QuickActions />
          </Section>

          <div className="grid gap-5 lg:grid-cols-3 lg:gap-6">
            <Section
              title="Recent runs"
              className="lg:col-span-2"
              description="Latest task executions — PASS/FAIL and publication when available."
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

            <div className="space-y-5">
              <Section
                title="Active executions"
                description="Queued, running, and grading right now."
                actions={
                  snapshot.activeRuns.length > 0 ? (
                    <Button asChild variant="ghost" size="sm" className="text-[var(--ef-accent)]">
                      <Link href="/runs">View all</Link>
                    </Button>
                  ) : null
                }
              >
                <ActiveExecution
                  runs={snapshot.activeRuns}
                  projectNameById={snapshot.projectNameById}
                  agentNameByVersionId={snapshot.agentNameByVersionId}
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

          <Text variant="caption" className="block text-muted-foreground">
            Health and feeds sample up to eight recent projects — open Projects or Runs for the full
            inventory.
          </Text>
        </div>
      </FadeIn>
    </PageLayout>
  );
}
