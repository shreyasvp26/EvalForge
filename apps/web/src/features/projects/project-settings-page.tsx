"use client";

import { Badge, Button, Input, Label, Plus, Text, Trash2, toast } from "@agent-eval/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { z } from "zod";

import { DeprecateProjectDialog } from "./deprecate-project-dialog";
import {
  formatProjectDate,
  projectQueryKey,
  projectsQueryKey,
  projectStatusBadge,
  projectStatusLabel,
} from "./utils";

import { ErrorContent } from "@/components/layouts/error-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { InlineError } from "@/components/patterns/inline-error";
import { NotFoundState } from "@/components/patterns/not-found-state";
import { PermissionDeniedState } from "@/components/patterns/permission-denied-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { ApiError } from "@/lib/api/client";
import { getProject, renameProject, updateProjectSettings } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

interface SettingRow {
  id: string;
  key: string;
  value: string;
}

const renameSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200, "Name is too long"),
});

function rowsFromSettings(settings: Record<string, string>): SettingRow[] {
  const entries = Object.entries(settings);
  if (entries.length === 0) {
    return [{ id: crypto.randomUUID(), key: "", value: "" }];
  }
  return entries.map(([key, value]) => ({
    id: crypto.randomUUID(),
    key,
    value,
  }));
}

function settingsFromRows(rows: SettingRow[]): Record<string, string> | { error: string } {
  const result: Record<string, string> = {};
  for (const row of rows) {
    const key = row.key.trim();
    const value = row.value;
    if (!key && !value.trim()) continue;
    if (!key) return { error: "Every setting with a value needs a key." };
    if (key in result) return { error: `Duplicate setting key: ${key}` };
    result[key] = value;
  }
  return result;
}

export function ProjectSettingsPage({ projectId }: { projectId: string }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const nameId = useId();
  const [deprecateOpen, setDeprecateOpen] = useState(false);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [rows, setRows] = useState<SettingRow[]>([]);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: projectQueryKey(projectId),
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getProject(token, projectId);
    },
  });

  useEffect(() => {
    if (!query.data) return;
    setName(query.data.name);
    setRows(rowsFromSettings(query.data.settings));
  }, [query.data]);

  const renameMutation = useMutation({
    mutationFn: async (nextName: string) => {
      if (!token) throw new Error("Missing auth token");
      return renameProject(token, projectId, nextName);
    },
    onSuccess: async (project) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
        queryClient.setQueryData(projectQueryKey(projectId), project),
      ]);
      toast.success("Project renamed", { description: project.name });
    },
    onError: (cause) => {
      const message = cause instanceof ApiError ? cause.message : "Could not rename the project.";
      toast.error("Rename failed", { description: message });
    },
  });

  const settingsMutation = useMutation({
    mutationFn: async (settings: Record<string, string>) => {
      if (!token) throw new Error("Missing auth token");
      return updateProjectSettings(token, projectId, settings);
    },
    onSuccess: async (project) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
        queryClient.setQueryData(projectQueryKey(projectId), project),
      ]);
      setRows(rowsFromSettings(project.settings));
      toast.success("Settings saved");
    },
    onError: (cause) => {
      const message = cause instanceof ApiError ? cause.message : "Could not save settings.";
      toast.error("Save failed", { description: message });
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
          title="Couldn’t load settings"
          description={
            error instanceof ApiError
              ? error.message
              : "Something went wrong while loading project settings."
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
  const isDeprecated = project.status === "deprecated";
  const currentName = project.name;

  function onRename(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setNameError(null);
    const parsed = renameSchema.safeParse({ name });
    if (!parsed.success) {
      setNameError(parsed.error.issues[0]?.message ?? "Invalid name");
      return;
    }
    if (parsed.data.name === currentName) {
      toast.message("Name unchanged");
      return;
    }
    renameMutation.mutate(parsed.data.name);
  }

  function onSaveSettings(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setSettingsError(null);
    const next = settingsFromRows(rows);
    if ("error" in next) {
      setSettingsError(next.error);
      return;
    }
    settingsMutation.mutate(next);
  }

  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: "Workspace", href: "/projects" },
              { label: "Projects", href: "/projects" },
              { label: project.name, href: `/projects/${project.id}` },
              { label: "Settings" },
            ]}
          />
        }
        eyebrow="Project settings"
        title={project.name}
        description="Rename the project, replace opaque settings, or deprecate it."
        actions={
          <Button asChild variant="outline">
            <Link href={`/projects/${project.id}`}>Back to project</Link>
          </Button>
        }
      />

      <div className="mt-8 space-y-6">
        <Section title="Status">
          <div className="flex flex-wrap items-center gap-3">
            <Badge status={projectStatusBadge(project.status)}>
              {projectStatusLabel(project.status)}
            </Badge>
            <Text variant="caption">Created {formatProjectDate(project.created_at)}</Text>
          </div>
        </Section>

        <Section title="Rename" description="Updates the project display name.">
          <form onSubmit={onRename} className="max-w-md space-y-3" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor={nameId}>Name</Label>
              <Input
                id={nameId}
                value={name}
                disabled={renameMutation.isPending || isDeprecated}
                onChange={(event) => {
                  setName(event.target.value);
                  if (nameError) setNameError(null);
                }}
                aria-invalid={nameError ? true : undefined}
              />
              {nameError ? <InlineError>{nameError}</InlineError> : null}
            </div>
            <Button type="submit" loading={renameMutation.isPending} disabled={isDeprecated}>
              Save name
            </Button>
          </form>
        </Section>

        <Section
          title="Settings"
          description="Settings are a full replace of the string key/value map. Empty rows are ignored."
        >
          <form onSubmit={onSaveSettings} className="space-y-4" noValidate>
            {settingsError ? <InlineError density="block">{settingsError}</InlineError> : null}
            <div className="space-y-3">
              {rows.map((row, index) => (
                <div
                  key={row.id}
                  className="grid gap-2 rounded-[var(--ef-radius-control)] border border-border p-3 sm:grid-cols-[1fr_1fr_auto]"
                >
                  <div className="space-y-1.5">
                    <Label htmlFor={`${row.id}-key`}>Key</Label>
                    <Input
                      id={`${row.id}-key`}
                      value={row.key}
                      disabled={settingsMutation.isPending || isDeprecated}
                      placeholder="key"
                      onChange={(event) => {
                        const value = event.target.value;
                        setRows((current) =>
                          current.map((item, i) => (i === index ? { ...item, key: value } : item)),
                        );
                      }}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor={`${row.id}-value`}>Value</Label>
                    <Input
                      id={`${row.id}-value`}
                      value={row.value}
                      disabled={settingsMutation.isPending || isDeprecated}
                      placeholder="value"
                      onChange={(event) => {
                        const value = event.target.value;
                        setRows((current) =>
                          current.map((item, i) => (i === index ? { ...item, value } : item)),
                        );
                      }}
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      leftIcon={Trash2}
                      disabled={settingsMutation.isPending || isDeprecated || rows.length <= 1}
                      aria-label={`Remove setting row ${String(index + 1)}`}
                      onClick={() => {
                        setRows((current) => current.filter((_, i) => i !== index));
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                leftIcon={Plus}
                disabled={settingsMutation.isPending || isDeprecated}
                onClick={() => {
                  setRows((current) => [
                    ...current,
                    { id: crypto.randomUUID(), key: "", value: "" },
                  ]);
                }}
              >
                Add row
              </Button>
              <Button type="submit" loading={settingsMutation.isPending} disabled={isDeprecated}>
                Save settings
              </Button>
            </div>
          </form>
        </Section>

        <Section
          title="Danger zone"
          description="Deprecating marks the project inactive for new work. This cannot be undone from the UI."
        >
          {isDeprecated ? (
            <Text variant="secondary">This project is already deprecated.</Text>
          ) : (
            <Button
              type="button"
              variant="danger"
              onClick={() => {
                setDeprecateOpen(true);
              }}
            >
              Deprecate project
            </Button>
          )}
        </Section>
      </div>

      <DeprecateProjectDialog
        open={deprecateOpen}
        onOpenChange={setDeprecateOpen}
        projectId={project.id}
        projectName={project.name}
      />
    </PageLayout>
  );
}
