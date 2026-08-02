"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { DeprecateProjectDialog } from "./deprecate-project-dialog";
import {
  formatProjectDate,
  projectQueryKey,
  projectStatusBadge,
  projectStatusLabel,
} from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { ApiError } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export function ProjectDetailPage({ projectId }: { projectId: string }) {
  const { token } = useAuth();
  const [deprecateOpen, setDeprecateOpen] = useState(false);

  const query = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  if (query.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (query.isError) {
    const error = query.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="project"
            action={
              <Button asChild variant="outline">
                <Link href="/projects">Back to projects</Link>
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
                <Link href="/projects">Back to projects</Link>
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
          title="Couldn’t load project"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this project."
          }
          action={
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void query.refetch();
              }}
            >
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const project = query.data;
  if (!project) return null;

  const settingsEntries = Object.entries(project.settings);
  const isDeprecated = project.status === "deprecated";

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          breadcrumbs={
            <Breadcrumbs
              items={[
                { label: "Workspace", href: "/projects" },
                { label: "Projects", href: "/projects" },
                { label: project.name },
              ]}
            />
          }
          eyebrow="Project"
          title={project.name}
          description={
            project.description.trim()
              ? project.description
              : "No description provided for this project."
          }
          actions={
            <Cluster gap={2}>
              <Button asChild variant="outline">
                <Link href={`/projects/${project.id}/suites`}>Suites</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={`/projects/${project.id}/settings`}>Settings</Link>
              </Button>
              {!isDeprecated ? (
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => {
                    setDeprecateOpen(true);
                  }}
                >
                  Deprecate
                </Button>
              ) : null}
            </Cluster>
          }
        />

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <Section
            title="Overview"
            className="lg:col-span-2"
            description="Project identity and status."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={projectStatusBadge(project.status)}>
                    {projectStatusLabel(project.status)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Project ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {project.id}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {project.description.trim() ? project.description : "No description provided."}
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
                  {formatProjectDate(project.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Updated
                </Text>
                <Text as="div" variant="secondary">
                  Not tracked separately yet — created time is authoritative.
                </Text>
              </div>
            </dl>
          </Section>

          <Section
            title="Settings summary"
            className="lg:col-span-2"
            description="Opaque project settings (string key/value). Edit on the settings page."
            actions={
              <Button asChild size="sm" variant="ghost">
                <Link href={`/projects/${project.id}/settings`}>Edit settings</Link>
              </Button>
            }
          >
            {settingsEntries.length === 0 ? (
              <Text variant="secondary">No settings configured.</Text>
            ) : (
              <div className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border">
                <table className="w-full text-left">
                  <thead className="border-b border-border bg-muted/40">
                    <tr>
                      <th className="px-3 py-2">
                        <Text as="span" variant="caption">
                          Key
                        </Text>
                      </th>
                      <th className="px-3 py-2">
                        <Text as="span" variant="caption">
                          Value
                        </Text>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {settingsEntries.map(([key, value]) => (
                      <tr key={key} className="border-b border-border last:border-0">
                        <td className="px-3 py-2 align-top">
                          <Text
                            as="span"
                            variant="body"
                            className="font-mono text-[length:var(--ef-text-caption)]"
                          >
                            {key}
                          </Text>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <Text as="span" variant="secondary" className="break-all">
                            {value}
                          </Text>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <Section title="Quick actions" description="Common project operations.">
            <Cluster gap={2} className="flex-col items-stretch sm:items-start">
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/projects/${project.id}/suites`}>Open suites</Link>
              </Button>
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/projects/${project.id}/settings`}>Open settings</Link>
              </Button>
              <Button
                type="button"
                variant="outline"
                className="justify-start"
                onClick={() => {
                  void navigator.clipboard.writeText(project.id).then(
                    () => {
                      toast.success("Project ID copied");
                    },
                    () => {
                      toast.error("Could not copy project ID");
                    },
                  );
                }}
              >
                Copy project ID
              </Button>
              {!isDeprecated ? (
                <Button
                  type="button"
                  variant="danger"
                  className="justify-start"
                  onClick={() => {
                    setDeprecateOpen(true);
                  }}
                >
                  Deprecate project
                </Button>
              ) : null}
            </Cluster>
          </Section>
        </div>
      </FadeIn>

      <DeprecateProjectDialog
        open={deprecateOpen}
        onOpenChange={setDeprecateOpen}
        projectId={project.id}
        projectName={project.name}
      />
    </PageLayout>
  );
}
