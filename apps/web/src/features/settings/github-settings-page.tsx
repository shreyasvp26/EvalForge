"use client";

import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Text,
  toast,
} from "@agent-eval/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SettingsShell } from "./settings-shell";

import { Section } from "@/components/layouts/section";
import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import {
  createGitHubConnection,
  listGitHubConnections,
  revokeGitHubConnection,
} from "@/lib/api/github";
import { useAuth } from "@/lib/auth/auth-provider";

const connectionsQueryKey = ["github", "connections"] as const;

export function GitHubSettingsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [connectOpen, setConnectOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const connectionsQuery = useQuery({
    queryKey: connectionsQueryKey,
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGitHubConnections(token);
    },
  });

  const connectMutation = useMutation({
    mutationFn: async (input: { token: string; display_name: string }) => {
      if (!token) throw new Error("Missing auth token");
      return createGitHubConnection(token, {
        token: input.token,
        display_name: input.display_name || "GitHub",
        scopes: ["repo"],
      });
    },
    onSuccess: async () => {
      setConnectOpen(false);
      setFormError(null);
      toast.success("GitHub connected for publication");
      await queryClient.invalidateQueries({ queryKey: connectionsQueryKey });
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "Failed to connect GitHub";
      setFormError(message);
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (connectionId: string) => {
      if (!token) throw new Error("Missing auth token");
      return revokeGitHubConnection(token, connectionId);
    },
    onSuccess: async () => {
      toast.success("GitHub connection revoked");
      await queryClient.invalidateQueries({ queryKey: connectionsQueryKey });
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Failed to revoke connection");
    },
  });

  const active = (connectionsQuery.data?.items ?? []).filter((c) => c.status === "active");

  return (
    <SettingsShell>
      <Section
        title="GitHub publication"
        description="Connect a GitHub token so EvalForge can create a branch and pull request after a passed evaluation. Tokens are encrypted at rest and never shown again."
      >
        {connectionsQuery.isError ? (
          <InlineError
            title="Could not load GitHub connections"
            message={
              connectionsQuery.error instanceof ApiError
                ? connectionsQuery.error.message
                : "Unknown error"
            }
          />
        ) : null}

        <div className="mt-4 flex items-center justify-between gap-3">
          <Text variant="body" className="text-muted-foreground">
            Least privilege: use a fine-grained PAT with contents and pull-request write on selected
            repositories.
          </Text>
          <Button
            type="button"
            onClick={() => {
              setConnectOpen(true);
            }}
          >
            Connect GitHub
          </Button>
        </div>

        <ul className="mt-6 space-y-3">
          {active.length === 0 ? (
            <li>
              <Text variant="body" className="text-muted-foreground">
                No active GitHub connection. Publication after PASS will be skipped until one is
                added.
              </Text>
            </li>
          ) : (
            active.map((connection) => (
              <li
                key={connection.id}
                className="flex items-center justify-between gap-3 rounded-[var(--ef-radius-control)] border border-border px-4 py-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Text as="div" variant="body" className="font-medium">
                      {connection.display_name}
                    </Text>
                    <Badge variant="secondary">{connection.status}</Badge>
                  </div>
                  <Text variant="caption" className="text-muted-foreground">
                    {connection.github_login ? `@${connection.github_login} · ` : null}
                    {connection.masked_token}
                  </Text>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={revokeMutation.isPending}
                  onClick={() => {
                    revokeMutation.mutate(connection.id);
                  }}
                >
                  Revoke
                </Button>
              </li>
            ))
          )}
        </ul>
      </Section>

      <Dialog open={connectOpen} onOpenChange={setConnectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect GitHub</DialogTitle>
            <DialogDescription>
              Paste a personal access token with repository write access. The token is never
              returned by the API after create.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              const tokenValue = form.get("token");
              const nameValue = form.get("display_name");
              connectMutation.mutate({
                token: typeof tokenValue === "string" ? tokenValue : "",
                display_name: typeof nameValue === "string" ? nameValue : "",
              });
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="display_name">Label</Label>
              <Input id="display_name" name="display_name" placeholder="Work GitHub" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="token">Access token</Label>
              <Input id="token" name="token" type="password" autoComplete="off" required />
            </div>
            {formError ? <InlineError title="Could not connect" message={formError} /> : null}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setConnectOpen(false);
                }}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={connectMutation.isPending}>
                Save connection
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </SettingsShell>
  );
}
