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
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
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
          breadcrumbs={
            <Breadcrumbs
              items={[
                { label: "Workspace", href: "/projects" },
                { label: "Projects", href: "/projects" },
                { label: projectName, href: `/projects/${projectId}` },
                { label: "Cases", href: `/projects/${projectId}/cases` },
                { label: caseItem.name },
              ]}
            />
          }
          eyebrow="Case"
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
                variant="outline"
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
            title="Overview"
            className="lg:col-span-2"
            description="Case identity and linked prompt."
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

          <Section title="Metadata" description="Lifecycle timestamps from the Control Plane.">
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
            </dl>
          </Section>

          <Section
            title="Active versions"
            className="lg:col-span-3"
            description="Published case and prompt versions used for new evaluation work."
          >
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3 rounded-[var(--ef-radius-panel)] border border-border p-4">
                <Text as="div" variant="caption">
                  Active case version
                </Text>
                {currentCaseVersion ? (
                  <div className="space-y-2">
                    <Cluster gap={2} className="items-center">
                      <Text as="span" variant="body" className="font-medium">
                        Version {String(currentCaseVersion.version_number)}
                      </Text>
                      <Badge status={versionStatusBadge(currentCaseVersion.status)}>
                        {versionStatusLabel(currentCaseVersion.status)}
                      </Badge>
                    </Cluster>
                    <Text variant="secondary" className="line-clamp-3">
                      {currentCaseVersion.description}
                    </Text>
                    <Text variant="caption" className="font-mono">
                      {currentCaseVersion.commit_sha}
                    </Text>
                  </div>
                ) : (
                  <Text variant="secondary">
                    No active case version. Publish a draft to establish the task definition.
                  </Text>
                )}
              </div>
              <div className="space-y-3 rounded-[var(--ef-radius-panel)] border border-border p-4">
                <Text as="div" variant="caption">
                  Active prompt version
                </Text>
                {currentPromptVersion ? (
                  <div className="space-y-2">
                    <Cluster gap={2} className="items-center">
                      <Text as="span" variant="body" className="font-medium">
                        Version {String(currentPromptVersion.version_number)}
                      </Text>
                      <Badge status={versionStatusBadge(currentPromptVersion.status)}>
                        {versionStatusLabel(currentPromptVersion.status)}
                      </Badge>
                    </Cluster>
                    <Text
                      variant="secondary"
                      className="line-clamp-4 font-mono text-[length:var(--ef-text-caption)]"
                    >
                      {currentPromptVersion.content}
                    </Text>
                  </div>
                ) : (
                  <Text variant="secondary">
                    No active prompt version. Publish a prompt draft, or publish a case version that
                    pins a draft (auto-publishes the prompt).
                  </Text>
                )}
              </div>
            </div>
          </Section>

          <Section
            title="Prompt versions"
            className="lg:col-span-3"
            description="Draft → Active (publish) → Superseded. Prompt content is versioned independently of case versions."
            actions={
              !isDeprecated ? (
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
              ) : null
            }
          >
            <PromptVersionCards caseItem={caseItem} versions={promptVersions} />
          </Section>

          <Section
            title="Case versions"
            className="lg:col-span-3"
            description="Draft → Active (publish) → Superseded. Each version pins a repository checkout and a prompt version."
            actions={
              !isDeprecated ? (
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
              ) : null
            }
          >
            <CaseVersionCards caseItem={caseItem} versions={caseVersions} />
          </Section>

          <Section title="Quick actions" description="Common case operations.">
            <Cluster gap={2} className="flex-col items-stretch sm:items-start">
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/projects/${projectId}/cases`}>Back to cases</Link>
              </Button>
              {!isDeprecated ? (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    className="justify-start"
                    onClick={() => {
                      setPromptDraftOpen(true);
                    }}
                  >
                    Create prompt draft
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="justify-start"
                    onClick={() => {
                      setCaseDraftOpen(true);
                    }}
                  >
                    Create case draft
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    className="justify-start"
                    onClick={() => {
                      setDeprecateOpen(true);
                    }}
                  >
                    Deprecate case
                  </Button>
                </>
              ) : (
                <Text variant="secondary">This case is deprecated; new drafts are blocked.</Text>
              )}
            </Cluster>
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
