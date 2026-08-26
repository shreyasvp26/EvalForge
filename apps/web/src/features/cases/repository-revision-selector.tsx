"use client";

import {
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Text,
} from "@agent-eval/ui";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  canSubmitTaskRevision,
  githubHttpsUrl,
  isExactCommitSha,
  isGitHubNotConnectedError,
  shortSha,
} from "./repository-revision";

import type { GitHubRepoSummary } from "@/lib/api/github";

import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import {
  getGitHubBranchHead,
  listGitHubBranches,
  listGitHubConnections,
  listGitHubRepositories,
} from "@/lib/api/github";
import { useAuth } from "@/lib/auth/auth-provider";

export interface RepositoryRevisionValue {
  repositoryUrl: string;
  commitSha: string;
  branch: string | null;
  fullName: string | null;
}

export interface RepositoryRevisionSelectorProps {
  disabled?: boolean;
  repositoryUrl: string;
  commitSha: string;
  onChange: (value: RepositoryRevisionValue) => void;
  repositoryError?: string | null;
  commitError?: string | null;
  allowManualEntry?: boolean;
}

export function RepositoryRevisionSelector({
  disabled = false,
  repositoryUrl,
  commitSha,
  onChange,
  repositoryError = null,
  commitError = null,
  allowManualEntry = true,
}: RepositoryRevisionSelectorProps) {
  const { token } = useAuth();
  const [manualMode, setManualMode] = useState(false);
  const [selectedFullName, setSelectedFullName] = useState<string>("");
  const [selectedBranch, setSelectedBranch] = useState<string>("");

  const connectionsQuery = useQuery({
    queryKey: ["github", "connections", "task-revision"],
    enabled: Boolean(token) && !manualMode,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGitHubConnections(token);
    },
  });

  const hasActiveConnection = useMemo(
    () => (connectionsQuery.data?.items ?? []).some((c) => c.status === "active"),
    [connectionsQuery.data],
  );

  const reposQuery = useQuery({
    queryKey: ["github", "repositories", "task-revision"],
    enabled: Boolean(token) && !manualMode && hasActiveConnection,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGitHubRepositories(token, { limit: 100 });
    },
  });

  const selectedRepo: GitHubRepoSummary | null = useMemo(() => {
    if (!selectedFullName) return null;
    return (reposQuery.data?.items ?? []).find((r) => r.full_name === selectedFullName) ?? null;
  }, [reposQuery.data, selectedFullName]);

  const branchesQuery = useQuery({
    queryKey: ["github", "branches", selectedRepo?.owner, selectedRepo?.name],
    enabled: Boolean(token) && !manualMode && Boolean(selectedRepo),
    queryFn: async () => {
      if (!token || !selectedRepo) throw new Error("Missing auth or repository");
      return listGitHubBranches(token, selectedRepo.owner, selectedRepo.name, { limit: 100 });
    },
  });

  const headQuery = useQuery({
    queryKey: ["github", "head", selectedRepo?.owner, selectedRepo?.name, selectedBranch],
    enabled:
      Boolean(token) && !manualMode && Boolean(selectedRepo) && Boolean(selectedBranch.trim()),
    queryFn: async () => {
      if (!token || !selectedRepo || !selectedBranch) {
        throw new Error("Missing auth, repository, or branch");
      }
      return getGitHubBranchHead(token, selectedRepo.owner, selectedRepo.name, selectedBranch);
    },
  });

  useEffect(() => {
    if (!selectedRepo) {
      setSelectedBranch("");
      return;
    }
    const preferred = selectedRepo.default_branch;
    const available = branchesQuery.data?.items ?? [];
    if (available.length === 0) {
      setSelectedBranch(preferred);
      return;
    }
    if (preferred && available.some((b) => b.name === preferred)) {
      setSelectedBranch(preferred);
      return;
    }
    const first = available[0]?.name;
    if (first) setSelectedBranch(first);
  }, [selectedRepo, branchesQuery.data]);

  useEffect(() => {
    if (manualMode || !selectedRepo || !headQuery.data) return;
    const sha = headQuery.data.sha;
    if (!isExactCommitSha(sha)) return;
    const nextUrl = selectedRepo.html_url || githubHttpsUrl(selectedRepo.owner, selectedRepo.name);
    if (repositoryUrl === nextUrl && commitSha === sha) return;
    onChange({
      repositoryUrl: nextUrl,
      commitSha: sha,
      branch: selectedBranch || null,
      fullName: selectedRepo.full_name,
    });
  }, [
    manualMode,
    selectedRepo,
    selectedBranch,
    headQuery.data,
    repositoryUrl,
    commitSha,
    onChange,
  ]);

  const notConnected =
    isGitHubNotConnectedError(
      reposQuery.error instanceof ApiError ? reposQuery.error.code : undefined,
    ) ||
    (connectionsQuery.isSuccess && !hasActiveConnection);

  const loadError =
    connectionsQuery.error instanceof ApiError
      ? connectionsQuery.error.message
      : reposQuery.error instanceof ApiError
        ? reposQuery.error.message
        : branchesQuery.error instanceof ApiError
          ? branchesQuery.error.message
          : headQuery.error instanceof ApiError
            ? headQuery.error.message
            : null;

  if (manualMode && allowManualEntry) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Text variant="caption">Manual repository URL and commit SHA</Text>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={disabled}
            onClick={() => {
              setManualMode(false);
            }}
          >
            Use GitHub selector
          </Button>
        </div>
        <div className="grid gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="manual-repo-url">Repository URL</Label>
            <Input
              id="manual-repo-url"
              value={repositoryUrl}
              disabled={disabled}
              placeholder="https://github.com/org/repo"
              onChange={(event) => {
                onChange({
                  repositoryUrl: event.target.value,
                  commitSha,
                  branch: null,
                  fullName: null,
                });
              }}
              aria-invalid={repositoryError ? true : undefined}
            />
            {repositoryError ? <InlineError>{repositoryError}</InlineError> : null}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="manual-commit-sha">Commit SHA</Label>
            <Input
              id="manual-commit-sha"
              value={commitSha}
              disabled={disabled}
              className="font-mono"
              placeholder="abcdef0…"
              onChange={(event) => {
                onChange({
                  repositoryUrl,
                  commitSha: event.target.value,
                  branch: null,
                  fullName: null,
                });
              }}
              aria-invalid={commitError ? true : undefined}
            />
            {commitError ? <InlineError>{commitError}</InlineError> : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Text as="div" variant="body" className="font-medium">
          Repository revision
        </Text>
        {allowManualEntry ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={disabled}
            onClick={() => {
              setManualMode(true);
            }}
          >
            Enter URL manually
          </Button>
        ) : null}
      </div>

      {notConnected ? (
        <InlineError density="block" title="GitHub not connected">
          Connect GitHub to select a repository.{" "}
          <Link href="/settings/github" className="underline underline-offset-2">
            Open Settings → GitHub
          </Link>
        </InlineError>
      ) : null}

      {!notConnected && loadError ? <InlineError density="block">{loadError}</InlineError> : null}

      {!notConnected ? (
        <>
          <div className="space-y-1.5">
            <Label>Repository</Label>
            <Select
              {...(selectedFullName ? { value: selectedFullName } : {})}
              onValueChange={(value) => {
                setSelectedFullName(value);
                setSelectedBranch("");
                onChange({
                  repositoryUrl: "",
                  commitSha: "",
                  branch: null,
                  fullName: value,
                });
              }}
              disabled={disabled || reposQuery.isLoading}
            >
              <SelectTrigger aria-invalid={repositoryError ? true : undefined}>
                <SelectValue
                  placeholder={
                    reposQuery.isLoading ? "Loading repositories…" : "Select GitHub repository"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {(reposQuery.data?.items ?? []).map((repo) => (
                  <SelectItem key={repo.full_name} value={repo.full_name}>
                    {repo.full_name}
                    {repo.private ? " · private" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {repositoryError ? <InlineError>{repositoryError}</InlineError> : null}
          </div>

          <div className="space-y-1.5">
            <Label>Branch</Label>
            <Select
              {...(selectedBranch ? { value: selectedBranch } : {})}
              onValueChange={(value) => {
                setSelectedBranch(value);
                onChange({
                  repositoryUrl: selectedRepo
                    ? selectedRepo.html_url || githubHttpsUrl(selectedRepo.owner, selectedRepo.name)
                    : repositoryUrl,
                  commitSha: "",
                  branch: value,
                  fullName: selectedRepo?.full_name ?? null,
                });
              }}
              disabled={disabled || !selectedRepo || branchesQuery.isLoading}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    !selectedRepo
                      ? "Select a repository first"
                      : branchesQuery.isLoading
                        ? "Loading branches…"
                        : "Select branch"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {(branchesQuery.data?.items ?? []).map((branch) => (
                  <SelectItem key={branch.name} value={branch.name}>
                    {branch.name}
                    {selectedRepo?.default_branch === branch.name ? " · default" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Revision (exact commit)</Label>
            {headQuery.isLoading ? (
              <Text variant="caption">Resolving branch HEAD…</Text>
            ) : headQuery.data && isExactCommitSha(headQuery.data.sha) ? (
              <div className="rounded-[var(--ef-radius-control)] border border-border bg-muted/30 px-3 py-2">
                <Text as="div" variant="body" className="font-mono">
                  {shortSha(headQuery.data.sha)}
                </Text>
                <Text as="div" variant="caption" className="font-mono break-all">
                  {headQuery.data.sha}
                </Text>
                {headQuery.data.message ? (
                  <Text as="div" variant="caption" className="mt-1">
                    {headQuery.data.message}
                  </Text>
                ) : null}
                <Text as="div" variant="caption" className="mt-2">
                  Task will run against commit {shortSha(headQuery.data.sha)}
                  {selectedBranch ? ` (from branch ${selectedBranch})` : ""}. The branch tip is not
                  stored — only this exact SHA.
                </Text>
              </div>
            ) : (
              <Text variant="caption">
                Select a repository and branch to resolve an immutable commit SHA.
              </Text>
            )}
            {commitError ? <InlineError>{commitError}</InlineError> : null}
            {selectedRepo &&
            selectedBranch &&
            headQuery.isSuccess &&
            !canSubmitTaskRevision({ repositoryUrl, commitSha }) ? (
              <InlineError>Could not resolve a valid exact commit SHA.</InlineError>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
