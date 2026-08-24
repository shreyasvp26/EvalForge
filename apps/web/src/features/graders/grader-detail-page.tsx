"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { CreateGraderDraftDialog } from "./create-grader-draft-dialog";
import { GraderVersionCards } from "./grader-version-cards";
import {
  activeGraderVersion,
  entityStatusBadge,
  entityStatusLabel,
  familyStatusBadge,
  familyStatusLabel,
  formatGraderDate,
  graderQueryKey,
  sortGraderVersionsNewestFirst,
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
import { ApiError } from "@/lib/api/client";
import { getGrader } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

export function GraderDetailPage({ graderId }: { graderId: string }) {
  const { token } = useAuth();
  const [draftOpen, setDraftOpen] = useState(false);

  const graderQuery = useQuery({
    queryKey: graderQueryKey(graderId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getGrader(token, graderId);
    },
  });

  if (graderQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (graderQuery.isError) {
    const error = graderQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="grader"
            action={
              <Button asChild variant="outline">
                <Link href="/graders">Back to graders</Link>
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
                <Link href="/graders">Back to graders</Link>
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
          title="Couldn’t load grader"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this grader."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void graderQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const grader = graderQuery.data;
  if (!grader) return null;

  const current = activeGraderVersion(grader);
  const versions = sortGraderVersionsNewestFirst(grader.versions);
  const isDeprecated = grader.status === "deprecated";

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow="Grader"
          title={grader.name}
          description={
            grader.description.trim() ? grader.description : "Objective scoring for runs."
          }
          actions={
            <Cluster gap={2}>
              {!isDeprecated ? (
                <Button
                  type="button"
                  onClick={() => {
                    setDraftOpen(true);
                  }}
                >
                  Create draft
                </Button>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  void navigator.clipboard.writeText(grader.id).then(
                    () => {
                      toast.success("Grader ID copied");
                    },
                    () => {
                      toast.error("Could not copy grader ID");
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
            title="Identity"
            className="lg:col-span-2"
            description="Stable grader record from the Control Plane."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={entityStatusBadge(grader.status)}>
                    {entityStatusLabel(grader.status)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Family
                </Text>
                <div>
                  <Badge status={familyStatusBadge(grader.family)}>
                    {familyStatusLabel(grader.family)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Created
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {formatGraderDate(grader.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Grader ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {grader.id}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {grader.description.trim() ? grader.description : "No description provided."}
                </Text>
              </div>
            </dl>
          </Section>

          <Section title="Versions" description="Published specification used when scoring runs.">
            <dl className="space-y-4">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Version count
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(grader.versions.length)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Active version
                </Text>
                {current ? (
                  <Cluster gap={2} className="items-center">
                    <Text as="span" variant="body" className="font-medium">
                      v{String(current.version_number)} · {current.label}
                    </Text>
                    <Badge status={versionStatusBadge(current.status)}>
                      {versionStatusLabel(current.status)}
                    </Badge>
                  </Cluster>
                ) : (
                  <Text variant="secondary">None published</Text>
                )}
              </div>
              {isDeprecated ? (
                <Text variant="secondary">This grader is deprecated; new drafts are blocked.</Text>
              ) : null}
            </dl>
          </Section>

          <Section
            title="Usage"
            className="lg:col-span-3"
            description="Active specification applied when this grader scores a run."
          >
            {current ? (
              <pre className="max-h-64 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] leading-relaxed text-foreground whitespace-pre-wrap break-words">
                {current.specification}
              </pre>
            ) : (
              <Text variant="secondary">
                No active specification. Publish a draft to establish the scoring contract.
              </Text>
            )}
          </Section>

          <Section
            title="Version history"
            className="lg:col-span-3"
            description="Draft → Active (publish) → Superseded. Specification is read-only text."
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
            <GraderVersionCards grader={grader} versions={versions} />
          </Section>
        </div>
      </FadeIn>

      <CreateGraderDraftDialog open={draftOpen} onOpenChange={setDraftOpen} graderId={grader.id} />
    </PageLayout>
  );
}
