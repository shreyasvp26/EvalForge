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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Text,
  toast,
} from "@agent-eval/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { SettingsShell } from "./settings-shell";

import type { ProviderCatalogItem, ProviderConnection } from "@/lib/api/providers";

import { Section } from "@/components/layouts/section";
import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import {
  createProviderConnection,
  listProviderConnections,
  listProviders,
  revokeProviderConnection,
} from "@/lib/api/providers";
import { useAuth } from "@/lib/auth/auth-provider";

const providersQueryKey = ["providers", "catalog"] as const;
const connectionsQueryKey = ["providers", "connections"] as const;

export function ProvidersSettingsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [connectOpen, setConnectOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<ProviderCatalogItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const providersQuery = useQuery({
    queryKey: providersQueryKey,
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProviders(token);
    },
  });

  const connectionsQuery = useQuery({
    queryKey: connectionsQueryKey,
    enabled: Boolean(token),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listProviderConnections(token);
    },
  });

  const connectionsByProvider = useMemo(() => {
    const map = new Map<string, ProviderConnection[]>();
    for (const connection of connectionsQuery.data?.items ?? []) {
      if (connection.status !== "active") continue;
      const list = map.get(connection.provider_key) ?? [];
      list.push(connection);
      map.set(connection.provider_key, list);
    }
    return map;
  }, [connectionsQuery.data]);

  const connectMutation = useMutation({
    mutationFn: async (input: { provider_key: string; api_key: string; display_name: string }) => {
      if (!token) throw new Error("Missing auth token");
      return createProviderConnection(token, input);
    },
    onSuccess: () => {
      toast.success("Provider connected");
      void queryClient.invalidateQueries({ queryKey: providersQueryKey });
      void queryClient.invalidateQueries({ queryKey: connectionsQueryKey });
      setConnectOpen(false);
      setSelectedProvider(null);
      setFormError(null);
    },
    onError: (cause) => {
      setFormError(cause instanceof ApiError ? cause.message : "Could not save connection.");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (connectionId: string) => {
      if (!token) throw new Error("Missing auth token");
      return revokeProviderConnection(token, connectionId);
    },
    onSuccess: () => {
      toast.success("Connection revoked");
      void queryClient.invalidateQueries({ queryKey: providersQueryKey });
      void queryClient.invalidateQueries({ queryKey: connectionsQueryKey });
    },
    onError: (cause) => {
      toast.error(cause instanceof ApiError ? cause.message : "Could not revoke connection.");
    },
  });

  function openConnect(provider: ProviderCatalogItem) {
    setSelectedProvider(provider);
    setFormError(null);
    setConnectOpen(true);
  }

  const providers = providersQuery.data?.items ?? [];

  return (
    <SettingsShell
      title="Providers"
      description="Bring your own API keys for coding-agent providers. Keys are encrypted at rest and never shown again."
    >
      <Section
        title="Catalog"
        description="Only Google Gemini is live-capable for coding agents today. Other providers may store credentials but are not production-verified."
      >
        {providersQuery.isError ? (
          <InlineError density="block">Could not load providers.</InlineError>
        ) : null}
        <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
          {providers.map((provider) => {
            const active = connectionsByProvider.get(provider.provider_key) ?? [];
            const connected = active.length > 0;
            return (
              <li key={provider.provider_key} className="space-y-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Text as="div" variant="body" className="font-medium">
                        {provider.display_name}
                      </Text>
                      <Badge status={provider.live_capable ? "completed" : "queued"}>
                        {provider.live_capable ? "Live capable" : provider.status}
                      </Badge>
                      <Badge status={connected ? "completed" : "warning"}>
                        {connected ? "Connected" : "Not connected"}
                      </Badge>
                    </div>
                    {provider.notes ? (
                      <Text variant="caption" className="block max-w-xl">
                        {provider.notes}
                      </Text>
                    ) : null}
                  </div>
                  {provider.status !== "unsupported" ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        openConnect(provider);
                      }}
                    >
                      Connect
                    </Button>
                  ) : null}
                </div>
                {active.length > 0 ? (
                  <ul className="space-y-2">
                    {active.map((connection) => (
                      <li
                        key={connection.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--ef-radius-control)] border border-border bg-muted/30 px-3 py-2"
                      >
                        <div className="min-w-0">
                          <Text as="div" variant="body">
                            {connection.display_name}
                          </Text>
                          <Text as="div" variant="caption" className="font-mono">
                            {connection.masked_key}
                          </Text>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          loading={revokeMutation.isPending}
                          onClick={() => {
                            revokeMutation.mutate(connection.id);
                          }}
                        >
                          Revoke
                        </Button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      </Section>

      <ConnectProviderDialog
        open={connectOpen}
        provider={selectedProvider}
        providers={providers.filter((p) => p.status !== "unsupported")}
        formError={formError}
        submitting={connectMutation.isPending}
        onOpenChange={(next) => {
          if (connectMutation.isPending) return;
          setConnectOpen(next);
          if (!next) {
            setSelectedProvider(null);
            setFormError(null);
          }
        }}
        onSubmit={(values) => {
          setFormError(null);
          connectMutation.mutate(values);
        }}
      />
    </SettingsShell>
  );
}

function ConnectProviderDialog({
  open,
  provider,
  providers,
  formError,
  submitting,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  provider: ProviderCatalogItem | null;
  providers: ProviderCatalogItem[];
  formError: string | null;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: { provider_key: string; api_key: string; display_name: string }) => void;
}) {
  const [providerKey, setProviderKey] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [displayName, setDisplayName] = useState("");

  const effectiveProviderKey = provider?.provider_key ?? providerKey;

  function reset() {
    setProviderKey("");
    setApiKey("");
    setDisplayName("");
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Connect provider</DialogTitle>
          <DialogDescription>
            The API key is encrypted at rest. After saving you will only see a masked fingerprint.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!effectiveProviderKey || !apiKey.trim()) return;
            onSubmit({
              provider_key: effectiveProviderKey,
              api_key: apiKey.trim(),
              display_name: displayName.trim(),
            });
          }}
        >
          {formError ? <InlineError density="block">{formError}</InlineError> : null}
          <div className="space-y-1.5">
            <Label>Provider</Label>
            {provider ? (
              <Text variant="body">{provider.display_name}</Text>
            ) : (
              <Select
                {...(providerKey ? { value: providerKey } : {})}
                onValueChange={setProviderKey}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((item) => (
                    <SelectItem key={item.provider_key} value={item.provider_key}>
                      {item.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="provider-api-key">API key</Label>
            <Input
              id="provider-api-key"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(event) => {
                setApiKey(event.target.value);
              }}
              placeholder="Paste API key"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="provider-display-name">Display name (optional)</Label>
            <Input
              id="provider-display-name"
              value={displayName}
              onChange={(event) => {
                setDisplayName(event.target.value);
              }}
              placeholder="e.g. Personal Google"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={submitting}
              onClick={() => {
                reset();
                onOpenChange(false);
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={submitting}
              disabled={!effectiveProviderKey || !apiKey.trim()}
            >
              Save connection
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
