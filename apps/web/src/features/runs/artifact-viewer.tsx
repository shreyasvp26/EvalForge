"use client";

import {
  Badge,
  Button,
  Cluster,
  Copy,
  FileText,
  ScrollArea,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Text,
  toast,
} from "@agent-eval/ui";
import { useMemo, useState } from "react";

import {
  ARTIFACT_TABS,
  artifactLinkedPreview,
  artifactMetadataDocument,
  artifactsForTab,
  downloadTextFile,
  formatByteSize,
  formatRunDate,
  truncateId,
} from "./utils";

import type { ArtifactTabId } from "./utils";
import type { Artifact, ExecutionEvent } from "@/lib/api/runs";

import { downloadRunArtifact } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export interface ArtifactViewerProps {
  artifacts: Artifact[];
  events: ExecutionEvent[];
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
}

export function ArtifactViewer({
  artifacts,
  events,
  isLoading = false,
  errorMessage = null,
  onRetry,
}: ArtifactViewerProps) {
  const defaultTab = useMemo(() => {
    for (const item of ARTIFACT_TABS) {
      if (artifactsForTab(artifacts, item.id).length > 0) return item.id;
    }
    return "stdout" satisfies ArtifactTabId;
  }, [artifacts]);

  const [tab, setTab] = useState<ArtifactTabId>(defaultTab);
  const [selectedByTab, setSelectedByTab] = useState<Partial<Record<ArtifactTabId, string>>>({});

  if (isLoading) {
    return <Text variant="secondary">Loading artifacts…</Text>;
  }

  if (errorMessage) {
    return (
      <div className="space-y-3">
        <Text variant="secondary">{errorMessage}</Text>
        {onRetry ? (
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
      </div>
    );
  }

  if (artifacts.length === 0) {
    return <Text variant="secondary">No artifacts yet.</Text>;
  }

  return (
    <Tabs
      value={tab}
      onValueChange={(value) => {
        setTab(value as ArtifactTabId);
      }}
    >
      <TabsList>
        {ARTIFACT_TABS.map((item) => {
          const count = artifactsForTab(artifacts, item.id).length;
          return (
            <TabsTrigger key={item.id} value={item.id} disabled={count === 0}>
              {item.label}
              {count > 0 ? ` (${String(count)})` : ""}
            </TabsTrigger>
          );
        })}
      </TabsList>

      {ARTIFACT_TABS.map((item) => {
        const items = artifactsForTab(artifacts, item.id);
        const selected =
          items.find((artifact) => artifact.id === selectedByTab[item.id]) ?? items[0] ?? null;
        const preview = selected ? artifactLinkedPreview(selected, events) : null;

        return (
          <TabsContent key={item.id} value={item.id}>
            {items.length === 0 ? (
              <Text variant="secondary">No {item.label} artifacts.</Text>
            ) : (
              <div className="grid gap-4 lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
                <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
                  {items.map((artifact) => {
                    const active = selected?.id === artifact.id;
                    return (
                      <li key={artifact.id}>
                        <button
                          type="button"
                          className={
                            active
                              ? "w-full bg-muted px-3 py-2 text-left"
                              : "w-full px-3 py-2 text-left hover:bg-muted/60"
                          }
                          onClick={() => {
                            setSelectedByTab((current) => ({
                              ...current,
                              [item.id]: artifact.id,
                            }));
                          }}
                        >
                          <Text as="div" variant="body" className="font-medium">
                            {artifact.kind}
                          </Text>
                          <Text as="div" variant="caption" className="font-mono tabular-nums">
                            {formatByteSize(artifact.size_bytes)}
                          </Text>
                        </button>
                      </li>
                    );
                  })}
                </ul>

                {selected ? <ArtifactPane artifact={selected} preview={preview} /> : null}
              </div>
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}

function ArtifactPane({ artifact, preview }: { artifact: Artifact; preview: string | null }) {
  const { token } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const metadata = artifactMetadataDocument(artifact, preview);
  const viewText = preview ?? metadata;

  async function handleDownloadBytes() {
    if (!token) {
      toast.error("Sign in required to download");
      return;
    }
    setDownloading(true);
    try {
      const result = await downloadRunArtifact(token, artifact.run_id, artifact.id);
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${artifact.kind}-${truncateId(artifact.id, 8)}`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Download started");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-3 rounded-[var(--ef-radius-panel)] border border-border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <Cluster gap={2} className="items-center">
            <Badge status="neutral">{artifact.kind}</Badge>
            <Text variant="caption" className="font-mono">
              {truncateId(artifact.id, 14)}
            </Text>
          </Cluster>
          <Text variant="caption" className="break-all font-mono">
            {artifact.storage_key}
          </Text>
          <Text variant="caption" className="tabular-nums">
            {formatByteSize(artifact.size_bytes)} · {artifact.content_type} ·{" "}
            {formatRunDate(artifact.created_at)}
          </Text>
        </div>
        <Cluster gap={2}>
          <Button
            type="button"
            size="sm"
            variant="outline"
            leftIcon={Copy}
            onClick={() => {
              void navigator.clipboard.writeText(viewText).then(
                () => {
                  toast.success("Copied");
                },
                () => {
                  toast.error("Could not copy");
                },
              );
            }}
          >
            Copy
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            leftIcon={FileText}
            onClick={() => {
              downloadTextFile(
                `${artifact.kind}-${truncateId(artifact.id, 8)}.${preview ? "txt" : "json"}`,
                viewText,
                preview ? "text/plain" : "application/json",
              );
              toast.success("Metadata download started");
            }}
          >
            Metadata
          </Button>
          <Button
            type="button"
            size="sm"
            variant="primary"
            disabled={downloading}
            onClick={() => {
              void handleDownloadBytes();
            }}
          >
            {downloading ? "Downloading…" : "Download"}
          </Button>
        </Cluster>
      </div>

      <Text variant="caption">
        {preview
          ? "Inline preview from linked execution events. Use Download for stored artifact bytes."
          : "Use Download for stored artifact bytes from object storage."}
      </Text>

      <ScrollArea className="h-[min(24rem,50vh)] rounded-[var(--ef-radius-control)] border border-border bg-muted/40">
        <pre className="p-3 font-mono text-[length:var(--ef-text-caption)] whitespace-pre-wrap break-words">
          {viewText}
        </pre>
      </ScrollArea>
    </div>
  );
}
