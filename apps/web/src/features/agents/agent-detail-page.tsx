"use client";

import { Badge, Button, Cluster, FadeIn, Text, toast } from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AgentVersionCards } from "./agent-version-cards";
import { CreateAdapterDialog } from "./create-adapter-dialog";
import { CreateAgentDraftDialog } from "./create-agent-draft-dialog";
import {
  activeAgentVersion,
  adapterQueryKey,
  agentQueryKey,
  entityStatusBadge,
  entityStatusLabel,
  formatAgentDate,
  sortAgentVersionsNewestFirst,
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
import { getAdapter, getAgent } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export function AgentDetailPage({ agentId }: { agentId: string }) {
  const { token } = useAuth();
  const router = useRouter();
  const [agentDraftOpen, setAgentDraftOpen] = useState(false);
  const [adapterOpen, setAdapterOpen] = useState(false);

  const agentQuery = useQuery({
    queryKey: agentQueryKey(agentId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getAgent(token, agentId);
    },
  });

  const adapterId = agentQuery.data?.adapter_id ?? null;

  const adapterQuery = useQuery({
    queryKey: adapterId ? adapterQueryKey(adapterId) : ["adapters", "none"],
    enabled: Boolean(token) && Boolean(adapterId),
    queryFn: async () => {
      if (!token || !adapterId) throw new Error("Missing adapter context");
      return getAdapter(token, adapterId);
    },
  });

  if (agentQuery.isLoading) {
    return (
      <PageLayout>
        <DetailSkeleton withInspector={false} />
      </PageLayout>
    );
  }

  if (agentQuery.isError) {
    const error = agentQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageLayout>
          <NotFoundState
            resourceLabel="agent"
            action={
              <Button asChild variant="outline">
                <Link href="/agents">Back to agents</Link>
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
                <Link href="/agents">Back to agents</Link>
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
          title="Couldn’t load agent"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading this agent."
          }
          action={
            <Button type="button" variant="outline" onClick={() => void agentQuery.refetch()}>
              Try again
            </Button>
          }
        />
      </PageLayout>
    );
  }

  const agent = agentQuery.data;
  if (!agent) return null;

  const current = activeAgentVersion(agent);
  const versions = sortAgentVersionsNewestFirst(agent.versions);
  const isDeprecated = agent.status === "deprecated";
  const adapter = adapterQuery.data;
  const hasAdapter = Boolean(agent.adapter_id);

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow="Agent"
          title={agent.name}
          description={
            agent.description.trim() ? agent.description : "No description provided for this agent."
          }
          actions={
            <Cluster gap={2}>
              {!isDeprecated ? (
                <Button
                  type="button"
                  onClick={() => {
                    setAgentDraftOpen(true);
                  }}
                >
                  Create draft
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void navigator.clipboard.writeText(agent.id).then(
                    () => {
                      toast.success("Agent ID copied");
                    },
                    () => {
                      toast.error("Could not copy agent ID");
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
            description="Agent identity and connection status."
          >
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Status
                </Text>
                <div>
                  <Badge status={entityStatusBadge(agent.status)}>
                    {entityStatusLabel(agent.status)}
                  </Badge>
                </div>
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
                  {agent.id}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {agent.description.trim() ? agent.description : "No description provided."}
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
                  {formatAgentDate(agent.created_at)}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Versions
                </Text>
                <Text as="div" variant="body" className="tabular-nums">
                  {String(agent.versions.length)}
                </Text>
              </div>
            </dl>
          </Section>

          <Section
            title="Active version"
            className="lg:col-span-3"
            description="The published agent release used when targeting this agent on runs."
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
                {current.release_notes.trim() ? (
                  <Text variant="secondary" className="whitespace-pre-wrap">
                    {current.release_notes}
                  </Text>
                ) : (
                  <Text variant="secondary">No release notes for this version.</Text>
                )}
              </div>
            ) : (
              <Text variant="secondary">
                No active agent version. Publish a draft to establish the active release.
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
                    setAgentDraftOpen(true);
                  }}
                >
                  Create draft
                </Button>
              ) : null
            }
          >
            <AgentVersionCards agent={agent} versions={versions} />
          </Section>

          <Section
            title="Connected adapter"
            className="lg:col-span-3"
            description="Each agent connects to at most one adapter (1:1). Adapters are versioned independently."
            actions={
              !hasAdapter && !isDeprecated ? (
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    setAdapterOpen(true);
                  }}
                >
                  Connect adapter
                </Button>
              ) : null
            }
          >
            {!hasAdapter ? (
              <Text variant="secondary">
                No adapter connected. Connect an adapter before this agent can be targeted by runs.
              </Text>
            ) : adapterQuery.isLoading ? (
              <Text variant="secondary">Loading adapter…</Text>
            ) : adapterQuery.isError ? (
              <ErrorContent
                title="Couldn’t load adapter"
                description={
                  adapterQuery.error instanceof ApiError
                    ? adapterQuery.error.message
                    : "Something went wrong while loading the connected adapter."
                }
                action={
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void adapterQuery.refetch()}
                  >
                    Try again
                  </Button>
                }
              />
            ) : adapter ? (
              <div className="rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 space-y-2">
                    <Cluster gap={2} className="items-center">
                      <Text as="span" variant="body" className="font-medium">
                        {adapter.name}
                      </Text>
                      <Badge status={entityStatusBadge(adapter.status)}>
                        {entityStatusLabel(adapter.status)}
                      </Badge>
                    </Cluster>
                    <Text variant="caption" className="break-all font-mono text-muted-foreground">
                      {adapter.id}
                    </Text>
                    <Text variant="caption" className="tabular-nums">
                      {adapter.active_version_id
                        ? `Active version · ${
                            adapter.versions.find((v) => v.id === adapter.active_version_id)
                              ? `v${String(
                                  adapter.versions.find((v) => v.id === adapter.active_version_id)
                                    ?.version_number,
                                )}`
                              : adapter.active_version_id
                          }`
                        : "No active adapter version"}
                      {` · ${String(adapter.versions.length)} version${adapter.versions.length === 1 ? "" : "s"}`}
                    </Text>
                  </div>
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/agents/${agent.id}/adapters/${adapter.id}`}>Open adapter</Link>
                  </Button>
                </div>
              </div>
            ) : (
              <Text variant="secondary">Adapter record was not found.</Text>
            )}
          </Section>

          <Section title="Quick actions" description="Common agent operations.">
            <Cluster gap={2} className="flex-col items-stretch sm:items-start">
              <Button asChild variant="outline" className="justify-start">
                <Link href="/agents">Back to agents</Link>
              </Button>
              {!isDeprecated ? (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    className="justify-start"
                    onClick={() => {
                      setAgentDraftOpen(true);
                    }}
                  >
                    Create agent draft
                  </Button>
                  {!hasAdapter ? (
                    <Button
                      type="button"
                      variant="outline"
                      className="justify-start"
                      onClick={() => {
                        setAdapterOpen(true);
                      }}
                    >
                      Connect adapter
                    </Button>
                  ) : adapter ? (
                    <Button asChild variant="outline" className="justify-start">
                      <Link href={`/agents/${agent.id}/adapters/${adapter.id}`}>
                        Manage adapter
                      </Link>
                    </Button>
                  ) : null}
                </>
              ) : (
                <Text variant="secondary">This agent is deprecated; new drafts are blocked.</Text>
              )}
            </Cluster>
          </Section>
        </div>
      </FadeIn>

      <CreateAgentDraftDialog
        open={agentDraftOpen}
        onOpenChange={setAgentDraftOpen}
        agentId={agent.id}
      />
      <CreateAdapterDialog
        open={adapterOpen}
        onOpenChange={setAdapterOpen}
        agentId={agent.id}
        onCreated={(createdAdapterId) => {
          router.push(`/agents/${agent.id}/adapters/${createdAdapterId}`);
        }}
      />
    </PageLayout>
  );
}
