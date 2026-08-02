"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AdapterVersionCards } from "./adapter-version-cards";
import { CreateAdapterDraftDialog } from "./create-adapter-draft-dialog";
import {
  activeAdapterVersion,
  adapterQueryKey,
  agentQueryKey,
  entityStatusBadge,
  entityStatusLabel,
  formatAgentDate,
  sortAdapterVersionsNewestFirst,
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
import { getAdapter, getAgent } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export function AdapterDetailPage({ agentId, adapterId }: { agentId: string; adapterId: string }) {
  const { token } = useAuth();
  const [draftOpen, setDraftOpen] = useState(false);

  const agentQuery = useQuery({
    queryKey: agentQueryKey(agentId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getAgent(token, agentId);
    },
  });

  const adapterQuery = useQuery({
    queryKey: adapterQueryKey(adapterId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getAdapter(token, adapterId);
    },
  });

  if (agentQuery.isLoading || adapterQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (adapterQuery.isError) {
    const error = adapterQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="adapter"
            action={
              <Button asChild variant="outline">
                <Link href={`/agents/${agentId}`}>Back to agent</Link>
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
                <Link href={`/agents/${agentId}`}>Back to agent</Link>
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
          title="Couldn’t load adapter"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this adapter."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void adapterQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const adapter = adapterQuery.data;
  const agent = agentQuery.data;
  if (!adapter) return null;

  if (adapter.agent_id !== agentId) {
    return (
      <PageLayout>
        <NotFoundState
          resourceLabel="adapter"
          description="This adapter does not belong to the agent in the URL."
          action={
            <Button asChild variant="outline">
              <Link href={`/agents/${adapter.agent_id}/adapters/${adapter.id}`}>
                Open under correct agent
              </Link>
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const agentName = agent?.name ?? "Agent";
  const current = activeAdapterVersion(adapter);
  const versions = sortAdapterVersionsNewestFirst(adapter.versions);
  const isDeprecated = adapter.status === "deprecated";

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          breadcrumbs={
            <Breadcrumbs
              items={[
                { label: "Workspace", href: "/projects" },
                { label: "Agents", href: "/agents" },
                { label: agentName, href: `/agents/${agentId}` },
                { label: adapter.name },
              ]}
            />
          }
          eyebrow="Adapter"
          title={adapter.name}
          description="Vendor translation identity connected to this agent. Versioned independently of agent releases."
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
                variant="outline"
                onClick={() => {
                  void navigator.clipboard.writeText(adapter.id).then(
                    () => {
                      toast.success("Adapter ID copied");
                    },
                    () => {
                      toast.error("Could not copy adapter ID");
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
          <Section title="Overview" className="lg:col-span-2" description="Adapter identity.">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={entityStatusBadge(adapter.status)}>
                    {entityStatusLabel(adapter.status)}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Adapter ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {adapter.id}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Agent ID
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {adapter.agent_id}
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
                  {formatAgentDate(adapter.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Versions
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(adapter.versions.length)}
                </Text>
              </div>
            </dl>
          </Section>

          <Section
            title="Active version"
            className="lg:col-span-3"
            description="The published adapter mapping used with this agent on runs."
          >
            {current ? (
              <div className="space-y-2">
                <Cluster gap={2} className="items-center">
                  <Text as="span" variant="body" className="font-medium">
                    Version {String(current.version_number)} · {current.label}
                  </Text>
                  <Badge status={versionStatusBadge(current.status)}>
                    {versionStatusLabel(current.status)}
                  </Badge>
                </Cluster>
                {current.notes.trim() ? (
                  <Text variant="secondary" className="whitespace-pre-wrap">
                    {current.notes}
                  </Text>
                ) : (
                  <Text variant="secondary">No notes for this version.</Text>
                )}
              </div>
            ) : (
              <Text variant="secondary">
                No active adapter version. Publish a draft to establish the active mapping.
              </Text>
            )}
          </Section>

          <Section
            title="Version history"
            className="lg:col-span-3"
            description="Draft → Active (publish) → Superseded."
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
            <AdapterVersionCards adapter={adapter} versions={versions} />
          </Section>

          <Section title="Quick actions" description="Common adapter operations.">
            <Cluster gap={2} className="flex-col items-stretch sm:items-start">
              <Button asChild variant="outline" className="justify-start">
                <Link href={`/agents/${agentId}`}>Back to agent</Link>
              </Button>
              {!isDeprecated ? (
                <Button
                  type="button"
                  variant="outline"
                  className="justify-start"
                  onClick={() => {
                    setDraftOpen(true);
                  }}
                >
                  Create adapter draft
                </Button>
              ) : (
                <Text variant="secondary">This adapter is deprecated; new drafts are blocked.</Text>
              )}
            </Cluster>
          </Section>
        </div>
      </FadeIn>

      <CreateAdapterDraftDialog
        open={draftOpen}
        onOpenChange={setDraftOpen}
        adapterId={adapter.id}
        agentId={adapter.agent_id}
      />
    </PageLayout>
  );
}
