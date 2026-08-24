"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { CaseVersionCards } from "./case-version-cards";
import { CreateCaseDraftDialog } from "./create-case-draft-dialog";
import { CreatePromptDraftDialog } from "./create-prompt-draft-dialog";
import { DeprecateCaseDialog } from "./deprecate-case-dialog";
import { PromptVersionCards } from "./prompt-version-cards";
import {
  activeCaseVersion,
  activePromptVersion,
  caseQueryKey,
  caseStatusBadge,
  caseStatusLabel,
  formatCaseDate,
  sortCaseVersionsNewestFirst,
  sortPromptVersionsNewestFirst,
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
import { getCase } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function CaseDetailPage({ projectId, caseId }: { projectId: string; caseId: string }) {
  const { token } = useAuth();
  const [promptDraftOpen, setPromptDraftOpen] = useState(false);
  const [caseDraftOpen, setCaseDraftOpen] = useState(false);
  const [deprecateOpen, setDeprecateOpen] = useState(false);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  const caseQuery = useQuery({
    queryKey: caseQueryKey(caseId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getCase(token, caseId);
    },
  });

  if (projectQuery.isLoading || caseQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (caseQuery.isError) {
    const error = caseQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="case"
            action={
              <Button asChild variant="outline">
                <Link href={`/projects/${projectId}/cases`}>Back to cases</Link>
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
                <Link href={`/projects/${projectId}/cases`}>Back to cases</Link>
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
          title="Couldn’t load case"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this case."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void caseQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const caseItem = caseQuery.data;
  const project = projectQuery.data;
  if (!caseItem) return null;

  if (caseItem.project_id !== projectId) {
    return (
      <PageLayout>
        <NotFoundState
          resourceLabel="case"
          description="This case does not belong to the project in the URL."
          action={
            <Button asChild variant="outline">
              <Link href={`/projects/${caseItem.project_id}/cases/${caseItem.id}`}>
                Open in correct project
              </Link>
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const projectName = project?.name ?? "Project";
  const currentCaseVersion = activeCaseVersion(caseItem);
  const currentPromptVersion = activePromptVersion(caseItem);
  const caseVersions = sortCaseVersionsNewestFirst(caseItem.versions);
  const promptVersions = sortPromptVersionsNewestFirst(caseItem.prompt_versions);
  const isDeprecated = caseItem.status === "deprecated";

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow={`Case · ${projectName}`}
          title={caseItem.name}
          description={
            caseItem.description.trim()
              ? caseItem.description
              : "No description provided for this case."
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
                      setPromptDraftOpen(true);
                    }}
                  >
                    New prompt draft
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setCaseDraftOpen(true);
                    }}
                  >
                    New case draft
                  </Button>
                </>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  void navigator.clipboard.writeText(caseItem.id).then(
                    () => {
                      toast.success("Case ID copied");
                    },
                    () => {
                      toast.error("Could not copy case ID");
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
            title="Evaluation definition"
            className="lg:col-span-2"
            description="What this case evaluates and its current lifecycle state."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={caseStatusBadge(caseItem.status)}>
                    {caseStatusLabel(caseItem.status)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Case ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {caseItem.id}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {caseItem.description.trim() ? caseItem.description : "No description provided."}
                </Text>
              </div>
            </dl>
          </Section>

          <Section title="Lifecycle" description="Created time and version counts from the API.">
            <dl className="space-y-4">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Created
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {formatCaseDate(caseItem.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Case versions
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(caseItem.versions.length)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Prompt versions
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(caseItem.prompt_versions.length)}
                </Text>
              </div>
              {!isDeprecated ? (
                <div className="pt-1">
                  <Button
                    type="button"
                    variant="danger"
                    size="sm"
                    onClick={() => {
                      setDeprecateOpen(true);
                    }}
                  >
                    Deprecate case
                  </Button>
                </div>
              ) : (
                <Text variant="secondary">This case is deprecated; new drafts are blocked.</Text>
              )}
            </dl>
          </Section>

          <Section
            title="Prompt"
            className="lg:col-span-3"
            description="Linked prompt and the active published content used for evaluation."
          >
            <dl className="mb-6 grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Prompt ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {caseItem.prompt_id}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Active prompt version
                </Text>
                {currentPromptVersion ? (
                  <Cluster gap={2} className="items-center">
                    <Text as="span" variant="body" className="font-medium">
                      Version {String(currentPromptVersion.version_number)}
                    </Text>
                    <Badge status={versionStatusBadge(currentPromptVersion.status)}>
                      {versionStatusLabel(currentPromptVersion.status)}
                    </Badge>
                  </Cluster>
                ) : (
                  <Text variant="secondary">No active prompt version.</Text>
                )}
              </div>
            </dl>
            {currentPromptVersion ? (
              <div className="rounded-[var(--ef-radius-panel)] border border-border p-4">
                <Text as="div" variant="caption" className="mb-2">
                  Content
                </Text>
                <Text
                  variant="secondary"
                  className="whitespace-pre-wrap font-mono text-[length:var(--ef-text-caption)]"
                >
                  {currentPromptVersion.content}
                </Text>
              </div>
            ) : (
              <Text variant="secondary">
                Publish a prompt draft, or publish a case version that pins a draft (auto-publishes
                the prompt).
              </Text>
            )}
          </Section>

          <Section
            title="Active case version"
            className="lg:col-span-3"
            description="Published case version used for new evaluation work."
          >
            {currentCaseVersion ? (
              <div className="space-y-2 rounded-[var(--ef-radius-panel)] border border-border p-4">
                <Cluster gap={2} className="items-center">
                  <Text as="span" variant="body" className="font-medium">
                    Version {String(currentCaseVersion.version_number)}
                  </Text>
                  <Badge status={versionStatusBadge(currentCaseVersion.status)}>
                    {versionStatusLabel(currentCaseVersion.status)}
                  </Badge>
                </Cluster>
                <Text variant="secondary">{currentCaseVersion.description}</Text>
                <Text variant="caption" className="font-mono">
                  {currentCaseVersion.commit_sha}
                </Text>
              </div>
            ) : (
              <Text variant="secondary">
                No active case version. Publish a draft to establish the task definition.
              </Text>
            )}
          </Section>

          <Section
            title="Versions"
            className="lg:col-span-3"
            description="Prompt and case version history. Draft → Active (publish) → Superseded."
          >
            <div className="space-y-8">
              <div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <Text as="div" variant="body" className="font-medium">
                    Prompt versions
                  </Text>
                  {!isDeprecated ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setPromptDraftOpen(true);
                      }}
                    >
                      Create prompt draft
                    </Button>
                  ) : null}
                </div>
                <PromptVersionCards caseItem={caseItem} versions={promptVersions} />
              </div>
              <div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <Text as="div" variant="body" className="font-medium">
                    Case versions
                  </Text>
                  {!isDeprecated ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setCaseDraftOpen(true);
                      }}
                    >
                      Create case draft
                    </Button>
                  ) : null}
                </div>
                <CaseVersionCards caseItem={caseItem} versions={caseVersions} />
              </div>
            </div>
          </Section>
        </div>
      </FadeIn>

      <CreatePromptDraftDialog
        open={promptDraftOpen}
        onOpenChange={setPromptDraftOpen}
        caseId={caseItem.id}
        projectId={caseItem.project_id}
      />
      <CreateCaseDraftDialog
        open={caseDraftOpen}
        onOpenChange={setCaseDraftOpen}
        caseItem={caseItem}
      />
      <DeprecateCaseDialog
        open={deprecateOpen}
        onOpenChange={setDeprecateOpen}
        caseId={caseItem.id}
        projectId={caseItem.project_id}
        caseName={caseItem.name}
      />
    </PageLayout>
  );
}
