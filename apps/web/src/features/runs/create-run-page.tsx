"use client";

import {
  Button,
  Checkbox,
  Cluster,
  FadeIn,
  Input,
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
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { InlineError } from "@/components/patterns/inline-error";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { adapterQueryKey, agentsQueryKey } from "@/features/agents/utils";
import { casesQueryKey } from "@/features/cases/utils";
import { gradersQueryKey, versionStatusLabel } from "@/features/graders/utils";
import { projectsQueryKey } from "@/features/projects/utils";
import { getAdapter, listAgents } from "@/lib/api/agents";
import { getCase, listCases } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { listGraders } from "@/lib/api/graders";
import { listProjects } from "@/lib/api/projects";
import { createRun } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

const STEPS = ["Project", "Case", "Prompt", "Agent", "Graders", "Review"] as const;

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
  const [platformVersionId, setPlatformVersionId] = useState("platform-1.0.0");
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

  const caseVersions = useMemo(() => {
    const versions = caseQuery.data?.versions ?? [];
    return [...versions].sort((a, b) => b.version_number - a.version_number);
  }, [caseQuery.data]);

  const promptVersions = useMemo(() => {
    const versions = caseQuery.data?.prompt_versions ?? [];
    return [...versions].filter((v) => v.status !== "retired");
  }, [caseQuery.data]);

  const agentVersions = useMemo(() => {
    const versions = selectedAgent?.versions ?? [];
    return [...versions].filter((v) => v.status !== "retired");
  }, [selectedAgent]);

  const adapterVersions = useMemo(() => {
    const versions = adapterQuery.data?.versions ?? [];
    return [...versions].filter((v) => v.status !== "retired");
  }, [adapterQuery.data]);

  const selectedGraders = useMemo(() => {
    return (gradersQuery.data?.items ?? []).filter((grader) => grader.id in graderSelections);
  }, [gradersQuery.data, graderSelections]);

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
  }

  function onSelectCaseVersion(nextVersionId: string) {
    setCaseVersionId(nextVersionId);
    const version = caseVersions.find((item) => item.id === nextVersionId);
    if (version?.prompt_version_id) {
      setPromptVersionId(version.prompt_version_id);
    }
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
      const grader = gradersQuery.data?.items.find((item) => item.id === graderId);
      const preferred =
        grader?.versions.find((version) => version.id === grader.active_version_id) ??
        grader?.versions.find((version) => version.status === "active") ??
        grader?.versions.find((version) => version.status === "draft");
      if (!preferred) return current;
      return { ...current, [graderId]: preferred.id };
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
          breadcrumbs={
            <Breadcrumbs
              items={[
                { label: "Workspace", href: "/projects" },
                { label: "Runs", href: "/runs" },
                { label: "New run" },
              ]}
            />
          }
          eyebrow="Execution"
          title="New run"
          description="Pin immutable versions, then launch. The worker queues immediately after create."
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
                  <Label>Case</Label>
                  <Select {...(caseId ? { value: caseId } : {})} onValueChange={onSelectCase}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a case" />
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
                  <Label>Case version</Label>
                  <Select
                    {...(caseVersionId ? { value: caseVersionId } : {})}
                    onValueChange={onSelectCaseVersion}
                    disabled={!caseId || caseQuery.isLoading}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select case version" />
                    </SelectTrigger>
                    <SelectContent>
                      {caseVersions.map((version) => (
                        <SelectItem key={version.id} value={version.id}>
                          {`v${String(version.version_number)} · ${versionStatusLabel(version.status)}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                            {`v${String(version.version_number)} · ${version.label}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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
                            {`v${String(version.version_number)} · ${version.label}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {!adapterId && agentId ? (
                      <Text variant="caption">Selected agent has no connected adapter.</Text>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {step === 4 ? (
              <div className="space-y-3">
                <Text variant="secondary">
                  Select one or more graders. Each selected grader pins a version (defaults to the
                  active version when available).
                </Text>
                <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
                  {(gradersQuery.data?.items ?? [])
                    .filter((grader) => grader.status !== "deprecated")
                    .map((grader) => {
                      const checked = grader.id in graderSelections;
                      const versions = [...grader.versions]
                        .filter((version) => version.status !== "retired")
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
                      label="Case version"
                      value={
                        caseVersion
                          ? `${caseName} · v${String(caseVersion.version_number)}`
                          : caseVersionId
                      }
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
                  <Label htmlFor="platform-version">Platform version ID</Label>
                  <Input
                    id="platform-version"
                    value={platformVersionId}
                    onChange={(event) => {
                      setPlatformVersionId(event.target.value);
                    }}
                    placeholder="platform-1.0.0"
                    className="font-mono"
                  />
                  <Text variant="caption">
                    Required pin. No platform catalog API exists yet — enter the Control Plane
                    platform version identifier.
                  </Text>
                </div>
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
