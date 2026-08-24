"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { CreateDraftVersionDialog } from "./create-draft-version-dialog";
import { SuiteCompositionViewer } from "./suite-composition-viewer";
import { SuiteVersionCards } from "./suite-version-cards";
import {
  activeVersion,
  formatSuiteDate,
  sortVersionsNewestFirst,
  suiteQueryKey,
  suiteStatusBadge,
  suiteStatusLabel,
  versionStatusBadge,
  versionStatusLabel,
} from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { projectQueryKey } from "@/features/projects/utils";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { getSuite } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

export function SuiteDetailPage({ projectId, suiteId }: { projectId: string; suiteId: string }) {
  const { token } = useAuth();
  const [draftOpen, setDraftOpen] = useState(false);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const suiteQuery = useQuery({
    queryKey: suiteQueryKey(suiteId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getSuite(token, suiteId);
    },
  });

  if (projectQuery.isLoading || suiteQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (suiteQuery.isError) {
    const error = suiteQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="suite"
            action={
              <Button asChild variant="outline">
                <Link href={`/projects/${projectId}/suites`}>Back to suites</Link>
              </Button>
            }
          />
        </PageLayout>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageLayout>
          <PermissionDeniedState
            action={
              <Button asChild variant="outline">
                <Link href={`/projects/${projectId}/suites`}>Back to suites</Link>
              </Button>
            }
          />
        </PageLayout>
      );
    }
    return (
      <PageLayout>
        <ErrorContent
          fill
          title="Couldn’t load suite"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this suite."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void suiteQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const suite = suiteQuery.data;
  const project = projectQuery.data;
  if (!suite) return null;

  if (suite.project_id !== projectId) {
    return (
      <PageLayout>
        <NotFoundState
          resourceLabel="suite"
          description="This suite does not belong to the project in the URL."
          action={
            <Button asChild variant="outline">
              <Link href={`/projects/${suite.project_id}/suites/${suite.id}`}>
                Open in correct project
              </Link>
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const projectName = project?.name ?? "Project";
  const current = activeVersion(suite);
  const versions = sortVersionsNewestFirst(suite.versions);
  const isDeprecated = suite.status === "deprecated";

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow={`Suite · ${projectName}`}
          title={suite.name}
          description={
            suite.description.trim() ? suite.description : "No description provided for this suite."
          }
          actions={
            <Cluster gap={2}>
              {!isDeprecated ? (
                <>
                  <Button asChild>
                    <Link href={`/runs/new?project=${encodeURIComponent(projectId)}`}>
                      Launch run
                    </Link>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setDraftOpen(true);
                    }}
                  >
                    Create draft
                  </Button>
                </>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  void navigator.clipboard.writeText(suite.id).then(
                    () => {
                      toast.success("Suite ID copied");
                    },
                    () => {
                      toast.error("Could not copy suite ID");
                    },
                  );
                }}
              >
                Copy ID
              </Button>
            </Cluster>
          }
        />

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <Section
            title="Suite definition"
            className="lg:col-span-2"
            description="Grouped case composition for evaluation runs."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={suiteStatusBadge(suite.status)}>
                    {suiteStatusLabel(suite.status)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Suite ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {suite.id}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {suite.description.trim() ? suite.description : "No description provided."}
                </Text>
              </div>
            </dl>
          </Section>

          <Section title="Lifecycle" description="Created time and version count from the API.">
            <dl className="space-y-4">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Created
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {formatSuiteDate(suite.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Versions
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(suite.versions.length)}
                </Text>
              </div>
              {isDeprecated ? (
                <Text variant="secondary">This suite is deprecated; new drafts are blocked.</Text>
              ) : null}
            </dl>
          </Section>

          <Section
            title="Active composition"
            className="lg:col-span-3"
            description="The published version used for new evaluation work."
          >
            {current ? (
              <div className="space-y-4">
                <Cluster gap={2} className="items-center">
                  <Text as="span" variant="body" className="font-medium">
                    Version {String(current.version_number)}
                  </Text>
                  <Badge status={versionStatusBadge(current.status)}>
                    {versionStatusLabel(current.status)}
                  </Badge>
                </Cluster>
                <SuiteCompositionViewer composition={current.composition} />
              </div>
            ) : (
              <SuiteCompositionViewer
                composition={[]}
                emptyTitle="No active version"
                emptyDescription="Publish a draft version to establish the active composition for this suite."
              />
            )}
          </Section>

          <Section
            title="Version history"
            className="lg:col-span-3"
            description="Draft → Active (publish) → Superseded or Retired."
            actions={
              !isDeprecated ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setDraftOpen(true);
                  }}
                >
                  Create draft
                </Button>
              ) : null
            }
          >
            <SuiteVersionCards suite={suite} versions={versions} />
          </Section>
        </div>
      </FadeIn>

      <CreateDraftVersionDialog
        open={draftOpen}
        onOpenChange={setDraftOpen}
        suiteId={suite.id}
        projectId={suite.project_id}
      />
    </PageLayout>
  );
}
