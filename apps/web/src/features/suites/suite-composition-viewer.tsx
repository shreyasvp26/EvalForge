"use client";

import { Icon, Layers, Text } from "@agent-eval/ui";

import type { SuiteCompositionEntry } from "@/lib/api/suites";

export interface SuiteCompositionViewerProps {
  composition: SuiteCompositionEntry[];
  emptyTitle?: string;
  emptyDescription?: string;
}

/**
 * Read-only ordered composition of case versions pinned in a suite version.
 */
export function SuiteCompositionViewer({
  composition,
  emptyTitle = "No composition yet",
  emptyDescription = "Create a draft version and add case versions to define execution order.",
}: SuiteCompositionViewerProps) {
  const ordered = [...composition].sort((a, b) => a.position - b.position);

  if (ordered.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2 rounded-[var(--ef-radius-panel)] border border-dashed border-border bg-muted/20 px-4 py-6">
        <Icon icon={Layers} size="md" className="text-muted-foreground" aria-hidden />
        <Text as="div" variant="body" className="font-medium">
          {emptyTitle}
        </Text>
        <Text as="div" variant="secondary">
          {emptyDescription}
        </Text>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border">
      <table className="w-full text-left">
        <thead className="border-b border-border bg-muted/40">
          <tr>
            <th className="w-20 px-3 py-2">
              <Text as="span" variant="caption">
                Order
              </Text>
            </th>
            <th className="px-3 py-2">
              <Text as="span" variant="caption">
                Case version
              </Text>
            </th>
            <th className="px-3 py-2">
              <Text as="span" variant="caption">
                Case project
              </Text>
            </th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((entry) => (
            <tr
              key={`${entry.case_version_id}-${String(entry.position)}`}
              className="border-b border-border last:border-0"
            >
              <td className="px-3 py-2 align-top">
                <Text as="span" variant="caption" className="tabular-nums">
                  {String(entry.position)}
                </Text>
              </td>
              <td className="px-3 py-2 align-top">
                <Text
                  as="span"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {entry.case_version_id}
                </Text>
              </td>
              <td className="px-3 py-2 align-top">
                <Text
                  as="span"
                  variant="secondary"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {entry.case_project_id}
                </Text>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
