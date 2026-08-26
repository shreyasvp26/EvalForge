"use client";

import {
  Button,
  Checkbox,
  Cluster,
  FadeIn,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Text,
  toast,
} from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { InlineError } from "@/components/patterns/inline-error";
import { adapterQueryKey, agentsQueryKey } from "@/features/agents/utils";
import {
  casesQueryKey,
  isPinnableVersionStatus,
  pinnableCaseVersions,
  pinnableRunPromptVersions,
  versionStatusLabel,
} from "@/features/cases/utils";
import { gradersQueryKey } from "@/features/graders/utils";
import { projectsQueryKey } from "@/features/projects/utils";
import { getAdapter, listAgents } from "@/lib/api/agents";
import { getCase, listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { listGraders } from "@/lib/api/graders";
import { listPlatforms, pinnablePlatformVersions } from "@/lib/api/platforms";
import { listProjects } from "@/lib/api/projects";
import { isGeminiAdapterPath, listModels, listProviderConnections } from "@/lib/api/providers";
import { createRun } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

const STEPS = ["Project", "Task", "Prompt", "Agent", "Graders", "Review"] as const;

function preferredPinnableVersionId(
  versions: { id: string; status: string; version_number: number }[],
  activeVersionId: string | null | undefined,
): string {
  const preferred =
    versions.find((version) => version.id === activeVersionId) ??
    versions.find((version) => version.status === "active") ??
    versions[0];
  return preferred?.id ?? "";
}

export function CreateRunPage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialProject = searchParams.get("project") ?? "";

  const [step, setStep] = useState(0);
  const [projectId, setProjectId] = useState(initialProject);
  const [caseId, setCaseId] = useState("");
  const [caseVersionId, setCaseVersionId] = useState("");
  const [promptVersionId, setPromptVersionId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [agentVersionId, setAgentVersionId] = useState("");
  const [adapterVersionId, setAdapterVersionId] = useState("");
  const [graderSelections, setGraderSelections] = useState<Record<string, string>>({});
  const [platformVersionId, setPlatformVersionId] = useState("");
  const [providerKey, setProviderKey] = useState("google");
  const [modelId, setModelId] = useState("");
  const [providerConnectionId, setProviderConnectionId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const projectsQuery = useQuery({
    queryKey: [...projectsQueryKey, "list", "create-run"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProjects(token, { limit: 100, sort: "-created_at" });
    },
  });

  const casesQuery = useQuery({
    queryKey: [...casesQueryKey(projectId), "list", "create-run"],
    enabled: Boolean(token) && Boolean(projectId),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listCases(token, { project_id: projectId, limit: 100, sort: "-created_at" });
    },
  });

  const caseQuery = useQuery({
    queryKey: ["cases", caseId, "create-run"],
    enabled: Boolean(token) && Boolean(caseId),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getCase(token, caseId);
    },
  });

  const agentsQuery = useQuery({
    queryKey: [...agentsQueryKey, "list", "create-run"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listAgents(token, { limit: 100, sort: "-created_at" });
    },
  });

  const selectedAgent = agentsQuery.data?.items.find((agent) => agent.id === agentId);
  const adapterId = selectedAgent?.adapter_id ?? null;

  const adapterQuery = useQuery({
    queryKey: adapterId ? adapterQueryKey(adapterId) : ["adapters", "none"],
    enabled: Boolean(token) && Boolean(adapterId),
    queryFn: async () => {
      if (!token || !adapterId) throw new Error("Missing adapter");
      return getAdapter(token, adapterId);
    },
  });

  const gradersQuery = useQuery({
    queryKey: [...gradersQueryKey, "list", "create-run"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGraders(token, { limit: 100, sort: "-created_at" });
    },
  });

  const showGeminiRuntime = isGeminiAdapterPath(adapterQuery.data?.name);

  const modelsQuery = useQuery({
    queryKey: ["models", "google", "create-run"],
    enabled: Boolean(token) && showGeminiRuntime,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listModels(token, { provider_key: "google" });
    },
  });

  const connectionsQuery = useQuery({
    queryKey: ["provider-connections", "create-run"],
    enabled: Boolean(token) && showGeminiRuntime,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProviderConnections(token);
    },
  });

  const platformsQuery = useQuery({
    queryKey: ["platforms", "list", "create-run"],
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listPlatforms(token, { limit: 100, sort: "-created_at" });
    },
  });

  const googleConnections = useMemo(() => {
    return (connectionsQuery.data?.items ?? []).filter(
      (connection) => connection.status === "active" && connection.provider_key === "google",
    );
  }, [connectionsQuery.data]);

  const platformOptions = useMemo(() => {
    const options: { value: string; label: string }[] = [];
    for (const platform of platformsQuery.data?.items ?? []) {
      for (const version of pinnablePlatformVersions(platform)) {
        options.push({
          value: version.id,
          label: `${platform.name} · v${String(version.version_number)} · ${version.label}`,
        });
      }
    }
    return options;
  }, [platformsQuery.data]);

  // Prefer the active version of the first catalog platform when none is chosen yet.
  useEffect(() => {
    if (platformVersionId || platformOptions.length === 0) return;
    const preferred =
      platformsQuery.data?.items
        .map((platform) => platform.active_version_id)
        .find((id): id is string => Boolean(id) && platformOptions.some((o) => o.value === id)) ??
      platformOptions[0]?.value;
    if (preferred) setPlatformVersionId(preferred);
  }, [platformOptions, platformVersionId, platformsQuery.data]);

  const caseVersions = useMemo(() => {
    if (!caseQuery.data) return [];
    return pinnableCaseVersions(caseQuery.data);
  }, [caseQuery.data]);

  const promptVersions = useMemo(() => {
    if (!caseQuery.data) return [];
    return pinnableRunPromptVersions(caseQuery.data);
  }, [caseQuery.data]);

  const agentVersions = useMemo(() => {
    const versions = selectedAgent?.versions ?? [];
    return [...versions]
      .filter((v) => isPinnableVersionStatus(v.status))
      .sort((a, b) => b.version_number - a.version_number);
  }, [selectedAgent]);

  const adapterVersions = useMemo(() => {
    const versions = adapterQuery.data?.versions ?? [];
    return [...versions]
      .filter((v) => isPinnableVersionStatus(v.status))
      .sort((a, b) => b.version_number - a.version_number);
  }, [adapterQuery.data]);

  const selectedCaseVersion = useMemo(
    () => caseVersions.find((version) => version.id === caseVersionId) ?? null,
    [caseVersions, caseVersionId],
  );

  const applicableGraderIds = useMemo(() => {
    return new Set(selectedCaseVersion?.applicable_grader_ids ?? []);
  }, [selectedCaseVersion]);

  const applicableGraders = useMemo(() => {
    return (gradersQuery.data?.items ?? []).filter(
      (grader) =>
        grader.status !== "deprecated" &&
        applicableGraderIds.has(grader.id) &&
        grader.versions.some((version) => isPinnableVersionStatus(version.status)),
    );
  }, [gradersQuery.data, applicableGraderIds]);

  const selectedGraders = useMemo(() => {
    return applicableGraders.filter((grader) => grader.id in graderSelections);
  }, [applicableGraders, graderSelections]);

  function canContinue(): boolean {
    if (step === 0) return Boolean(projectId);
    if (step === 1) return Boolean(caseId && caseVersionId);
    if (step === 2) return Boolean(promptVersionId);
    if (step === 3) return Boolean(agentId && agentVersionId && adapterVersionId);
    if (step === 4) return Object.keys(graderSelections).length > 0;
    if (step === 5) return Boolean(platformVersionId.trim());
    return false;
  }

  function onSelectCase(nextCaseId: string) {
    setCaseId(nextCaseId);
    setCaseVersionId("");
    setPromptVersionId("");
    setGraderSelections({});
  }

  function onSelectCaseVersion(nextVersionId: string) {
    setCaseVersionId(nextVersionId);
    setGraderSelections({});
    const version = caseVersions.find((item) => item.id === nextVersionId);
    if (version?.prompt_version_id) {
      const promptOk = promptVersions.some(
        (prompt) =>
          prompt.id === version.prompt_version_id && isPinnableVersionStatus(prompt.status),
      );
      if (promptOk) {
        setPromptVersionId(version.prompt_version_id);
        return;
      }
    }
    setPromptVersionId(
      preferredPinnableVersionId(promptVersions, caseQuery.data?.active_prompt_version_id),
    );
  }

  function onSelectAgent(nextAgentId: string) {
    setAgentId(nextAgentId);
    setAgentVersionId("");
    setAdapterVersionId("");
  }

  function toggleGrader(graderId: string, checked: boolean) {
    setGraderSelections((current) => {
      if (!checked) {
        const { [graderId]: _removed, ...rest } = current;
        return rest;
      }
      const grader = applicableGraders.find((item) => item.id === graderId);
      if (!grader) return current;
      const pinnable = grader.versions
        .filter((version) => isPinnableVersionStatus(version.status))
        .sort((a, b) => b.version_number - a.version_number);
      const preferredId = preferredPinnableVersionId(pinnable, grader.active_version_id);
      if (!preferredId) return current;
      return { ...current, [graderId]: preferredId };
    });
  }

  async function onLaunch() {
    setFormError(null);
    if (!token) {
      setFormError("You must be signed in to launch a run.");
      return;
    }
    if (!canContinue()) {
      setFormError("Complete all required pins before launching.");
      return;
    }

    setSubmitting(true);
    const idempotencyKey =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `create-run-${String(Date.now())}`;

    try {
      const run = await createRun(
        token,
        {
          project_id: projectId,
          case_id: caseId,
          case_version_id: caseVersionId,
          prompt_version_id: promptVersionId,
          agent_id: agentId,
          agent_version_id: agentVersionId,
          adapter_version_id: adapterVersionId,
          grader_version_refs: Object.entries(graderSelections).map(
            ([grader_id, grader_version_id]) => ({
              grader_id,
              grader_version_id,
            }),
          ),
          platform_version_id: platformVersionId.trim(),
          ...(showGeminiRuntime && modelId
            ? {
                provider_key: providerKey || "google",
                gateway_key: "direct",
                model_id: modelId,
                routing_mode: "fixed",
                provider_connection_id: providerConnectionId || null,
              }
            : {}),
        },
        idempotencyKey,
      );
      toast.success("Run launched", { description: `Status: ${run.status}` });
      router.push(`/runs/${run.id}`);
    } catch (cause) {
      setFormError(cause instanceof ApiError ? cause.message : "Could not launch the run.");
      setSubmitting(false);
    }
  }

  const projectName =
    projectsQuery.data?.items.find((project) => project.id === projectId)?.name ?? projectId;
  const caseName = caseQuery.data?.name ?? caseId;
  const caseVersion = caseVersions.find((version) => version.id === caseVersionId);
  const promptVersion = promptVersions.find((version) => version.id === promptVersionId);
  const agentVersion = agentVersions.find((version) => version.id === agentVersionId);
  const adapterVersion = adapterVersions.find((version) => version.id === adapterVersionId);

  return (
    <PageLayout>
      <FadeIn>
        <PageHeader
          eyebrow="Execution"
          title="New run"
          description="Select a task revision (exact commit), agent, and credentials — then launch. Failed evaluations never publish to GitHub."
          actions={
            <Button asChild variant="outline">
              <Link href="/runs">Cancel</Link>
            </Button>
          }
        />

        <Section
          className="mt-8"
          title="Launch wizard"
          description="Complete each step before review."
        >
          <ol className="mb-6 flex flex-wrap gap-2">
            {STEPS.map((label, index) => {
              const active = index === step;
              const done = index < step;
              return (
                <li key={label}>
                  <button
                    type="button"
                    className={
                      active
                        ? "rounded-full bg-foreground px-3 py-1 text-[length:var(--ef-text-caption)] font-medium text-background"
                        : done
                          ? "rounded-full bg-muted px-3 py-1 text-[length:var(--ef-text-caption)] font-medium text-foreground"
                          : "rounded-full border border-border px-3 py-1 text-[length:var(--ef-text-caption)] text-muted-foreground"
                    }
                    onClick={() => {
                      if (index <= step) setStep(index);
                    }}
                  >
                    {String(index + 1)}. {label}
                  </button>
                </li>
              );
            })}
          </ol>

          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="mt-4 space-y-4">
            {step === 0 ? (
              <div className="space-y-1.5">
                <Label>Project</Label>
                <Select
                  {...(projectId ? { value: projectId } : {})}
                  onValueChange={(value) => {
                    setProjectId(value);
                    setCaseId("");
                    setCaseVersionId("");
                    setPromptVersionId("");
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projectsQuery.data?.items.map((project) => (
                      <SelectItem key={project.id} value={project.id}>
                        {project.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : null}

            {step === 1 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Task</Label>
                  <Select {...(caseId ? { value: caseId } : {})} onValueChange={onSelectCase}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a task" />
                    </SelectTrigger>
                    <SelectContent>
                      {casesQuery.data?.items
                        .filter((item) => item.status !== "deprecated")
                        .map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Task version</Label>
                  <Select
                    {...(caseVersionId ? { value: caseVersionId } : {})}
                    onValueChange={onSelectCaseVersion}
                    disabled={!caseId || caseQuery.isLoading}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select task version" />
                    </SelectTrigger>
                    <SelectContent>
                      {caseVersions.map((version) => (
                        <SelectItem key={version.id} value={version.id}>
                          {`v${String(version.version_number)} · ${versionStatusLabel(version.status)}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {caseId && !caseQuery.isLoading && caseVersions.length === 0 ? (
                    <Text variant="caption">
                      No published task versions. Publish a draft before launching a run.
                    </Text>
                  ) : null}
                </div>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="space-y-1.5">
                <Label>Prompt version</Label>
                <Select
                  {...(promptVersionId ? { value: promptVersionId } : {})}
                  onValueChange={setPromptVersionId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select prompt version" />
                  </SelectTrigger>
                  <SelectContent>
                    {promptVersions.map((version) => (
                      <SelectItem key={version.id} value={version.id}>
                        {`v${String(version.version_number)} · ${versionStatusLabel(version.status)}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {promptVersions.length === 0 ? (
                  <Text variant="caption">
                    No published prompt versions. Publish a prompt draft before launching.
                  </Text>
                ) : null}
                {promptVersion ? (
                  <pre className="mt-3 max-h-48 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] whitespace-pre-wrap">
                    {promptVersion.content}
                  </pre>
                ) : null}
              </div>
            ) : null}

            {step === 3 ? (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <Label>Agent</Label>
                  <Select {...(agentId ? { value: agentId } : {})} onValueChange={onSelectAgent}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select an agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {agentsQuery.data?.items.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id} disabled={!agent.adapter_id}>
                          {agent.name}
                          {!agent.adapter_id ? " (no adapter)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>Agent version</Label>
                    <Select
                      {...(agentVersionId ? { value: agentVersionId } : {})}
                      onValueChange={setAgentVersionId}
                      disabled={!agentId}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select agent version" />
                      </SelectTrigger>
                      <SelectContent>
                        {agentVersions.map((version) => (
                          <SelectItem key={version.id} value={version.id}>
                            {`v${String(version.version_number)} · ${version.label} · ${versionStatusLabel(version.status)}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {agentId && agentVersions.length === 0 ? (
                      <Text variant="caption">
                        No published agent versions. Publish an agent draft first.
                      </Text>
                    ) : null}
                  </div>
                  <div className="space-y-1.5">
                    <Label>Adapter version</Label>
                    <Select
                      {...(adapterVersionId ? { value: adapterVersionId } : {})}
                      onValueChange={setAdapterVersionId}
                      disabled={!adapterId || adapterQuery.isLoading}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select adapter version" />
                      </SelectTrigger>
                      <SelectContent>
                        {adapterVersions.map((version) => (
                          <SelectItem key={version.id} value={version.id}>
                            {`v${String(version.version_number)} · ${version.label} · ${versionStatusLabel(version.status)}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {!adapterId && agentId ? (
                      <Text variant="caption">Selected agent has no connected adapter.</Text>
                    ) : null}
                    {adapterId && !adapterQuery.isLoading && adapterVersions.length === 0 ? (
                      <Text variant="caption">
                        No published adapter versions. Publish an adapter draft first.
                      </Text>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {step === 4 ? (
              <div className="space-y-3">
                <Text variant="secondary">
                  Select graders declared on this task version. Only published versions can be
                  pinned.
                </Text>
                {!caseVersionId ? (
                  <Text variant="secondary">Select a task version first.</Text>
                ) : applicableGraderIds.size === 0 ? (
                  <Text variant="secondary">
                    This task version declares no applicable graders. Edit the task version to add
                    grader IDs, then publish it.
                  </Text>
                ) : applicableGraders.length === 0 ? (
                  <Text variant="secondary">
                    Declared graders were not found or have no published versions. Check task
                    declarations and publish grader versions.
                  </Text>
                ) : (
                  <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
                    {applicableGraders.map((grader) => {
                      const checked = grader.id in graderSelections;
                      const versions = [...grader.versions]
                        .filter((version) => isPinnableVersionStatus(version.status))
                        .sort((a, b) => b.version_number - a.version_number);
                      return (
                        <li key={grader.id} className="space-y-3 p-4">
                          <label className="flex items-center gap-3">
                            <Checkbox
                              checked={checked}
                              onCheckedChange={(value) => {
                                toggleGrader(grader.id, value === true);
                              }}
                              disabled={versions.length === 0}
                            />
                            <span className="font-medium">{grader.name}</span>
                            <Text as="span" variant="caption">
                              {grader.family}
                            </Text>
                          </label>
                          {checked ? (
                            <Select
                              {...(graderSelections[grader.id]
                                ? { value: graderSelections[grader.id] }
                                : {})}
                              onValueChange={(value) => {
                                setGraderSelections((current) => ({
                                  ...current,
                                  [grader.id]: value,
                                }));
                              }}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select grader version" />
                              </SelectTrigger>
                              <SelectContent>
                                {versions.map((version) => (
                                  <SelectItem key={version.id} value={version.id}>
                                    {`v${String(version.version_number)} · ${version.label} · ${versionStatusLabel(version.status)}`}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            ) : null}

            {step === 5 ? (
              <div className="space-y-6">
                <div className="rounded-[var(--ef-radius-panel)] border border-border p-4">
                  <Text as="div" variant="caption" className="mb-3">
                    Pinned versions
                  </Text>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <PinRow label="Project" value={projectName} />
                    <PinRow
                      label="Task version"
                      value={
                        caseVersion
                          ? `${caseName} · v${String(caseVersion.version_number)}`
                          : caseVersionId
                      }
                    />
                    <PinRow
                      label="Repository"
                      value={selectedCaseVersion?.repository_url.trim() ?? "—"}
                    />
                    <PinRow
                      label="Exact commit SHA"
                      value={selectedCaseVersion?.commit_sha.trim() ?? "—"}
                    />
                    <PinRow
                      label="Prompt version"
                      value={
                        promptVersion ? `v${String(promptVersion.version_number)}` : promptVersionId
                      }
                    />
                    <PinRow
                      label="Agent version"
                      value={
                        agentVersion
                          ? `${selectedAgent?.name ?? "Agent"} · v${String(agentVersion.version_number)} · ${agentVersion.label}`
                          : agentVersionId
                      }
                    />
                    <PinRow
                      label="Adapter version"
                      value={
                        adapterVersion
                          ? `${adapterQuery.data?.name ?? "Adapter"} · v${String(adapterVersion.version_number)} · ${adapterVersion.label}`
                          : adapterVersionId
                      }
                    />
                    <div className="space-y-1 sm:col-span-2">
                      <Text as="div" variant="caption">
                        Grader versions
                      </Text>
                      <ul className="space-y-1">
                        {selectedGraders.map((grader) => {
                          const version = grader.versions.find(
                            (item) => item.id === graderSelections[grader.id],
                          );
                          return (
                            <li key={grader.id}>
                              <Text variant="body">
                                {grader.name}
                                {version
                                  ? ` · v${String(version.version_number)} · ${version.label}`
                                  : ""}
                              </Text>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  </dl>
                </div>

                <div className="space-y-1.5">
                  <Label>Platform</Label>
                  {platformsQuery.isError ? (
                    <InlineError density="block">
                      {platformsQuery.error instanceof ApiError
                        ? platformsQuery.error.message
                        : "Could not load platforms."}
                    </InlineError>
                  ) : null}
                  {platformsQuery.isSuccess && platformOptions.length === 0 ? (
                    <InlineError density="block">
                      No platform versions are published yet. Create and publish a platform in the
                      catalog before launching a run.
                    </InlineError>
                  ) : null}
                  <Select
                    {...(platformVersionId ? { value: platformVersionId } : {})}
                    onValueChange={setPlatformVersionId}
                    disabled={platformOptions.length === 0}
                  >
                    <SelectTrigger aria-label="Platform version">
                      <SelectValue placeholder="Select platform version" />
                    </SelectTrigger>
                    <SelectContent>
                      {platformOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Text variant="caption">
                    Required sandbox policy pin. Failed evaluations never create a branch or PR.
                  </Text>
                </div>

                {showGeminiRuntime ? (
                  <div className="space-y-4 rounded-[var(--ef-radius-panel)] border border-border p-4">
                    <div>
                      <Text as="div" variant="caption" className="mb-1">
                        Model & credential
                      </Text>
                      <Text variant="caption" className="mt-1 block">
                        Exact model pin for Gemini CLI. Credential stays encrypted — only a
                        reference is stored on the run.
                      </Text>
                      <Text variant="caption">
                        Gemini path only. Exact model pinning uses fixed routing and the direct
                        gateway.
                      </Text>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label>Provider</Label>
                        <Select value={providerKey} onValueChange={setProviderKey}>
                          <SelectTrigger>
                            <SelectValue placeholder="Provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="google">Google</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label>Model</Label>
                        <Select {...(modelId ? { value: modelId } : {})} onValueChange={setModelId}>
                          <SelectTrigger>
                            <SelectValue placeholder="Optional model pin" />
                          </SelectTrigger>
                          <SelectContent>
                            {modelsQuery.data?.items.map((model) => (
                              <SelectItem key={model.model_id} value={model.model_id}>
                                {model.display_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label>Credential</Label>
                        <Select
                          {...(providerConnectionId ? { value: providerConnectionId } : {})}
                          onValueChange={setProviderConnectionId}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Optional BYOK connection" />
                          </SelectTrigger>
                          <SelectContent>
                            {googleConnections.map((connection) => (
                              <SelectItem key={connection.id} value={connection.id}>
                                {connection.display_name} · {connection.masked_key}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {googleConnections.length === 0 ? (
                          <Text variant="caption">
                            No Google connections yet. Add one under Settings → Providers.
                          </Text>
                        ) : null}
                      </div>
                      <div className="space-y-1.5">
                        <Label>Gateway / routing</Label>
                        <Text as="div" variant="body">
                          direct · fixed
                        </Text>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <Cluster gap={2} className="mt-8 justify-between">
            <Button
              type="button"
              variant="outline"
              disabled={step === 0 || submitting}
              onClick={() => {
                setFormError(null);
                setStep((current) => Math.max(0, current - 1));
              }}
            >
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button
                type="button"
                disabled={!canContinue()}
                onClick={() => {
                  setFormError(null);
                  setStep((current) => Math.min(STEPS.length - 1, current + 1));
                }}
              >
                Continue
              </Button>
            ) : (
              <Button
                type="button"
                loading={submitting}
                disabled={!canContinue()}
                onClick={() => void onLaunch()}
              >
                Launch run
              </Button>
            )}
          </Cluster>
        </Section>
      </FadeIn>
    </PageLayout>
  );
}

function PinRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <Text as="div" variant="caption">
        {label}
      </Text>
      <Text as="div" variant="body" className="break-all">
        {value || "—"}
      </Text>
    </div>
  );
}
