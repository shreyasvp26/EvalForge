"use client";

import { Badge, Button, ChevronDown, ChevronRight, Cluster, Icon, Text } from "@agent-eval/ui";
import { useState } from "react";

import { formatScoreValue, pendingGraderSlots, scoreResultBadge, truncateId } from "./utils";

import type { Score } from "@/lib/api/runs";

export interface ScoreViewerProps {
  scores: Score[];
  expectedGraderCount: number;
  isPartiallyGraded: boolean;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
}

export function ScoreViewer({
  scores,
  expectedGraderCount,
  isPartiallyGraded,
  isLoading = false,
  errorMessage = null,
  onRetry,
}: ScoreViewerProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const pending = pendingGraderSlots(expectedGraderCount, scores);

  if (isLoading) {
    return <Text variant="secondary">Loading scores…</Text>;
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

  return (
    <div className="space-y-4">
      <Cluster gap={2} className="items-center">
        <Text variant="caption">
          {String(scores.length)} of {String(expectedGraderCount)} graders reported
        </Text>
        {isPartiallyGraded || pending > 0 ? (
          <Badge status="warning">{pending > 0 ? `${String(pending)} pending` : "Partial"}</Badge>
        ) : scores.length > 0 ? (
          <Badge status="completed">Complete</Badge>
        ) : null}
      </Cluster>

      {scores.length === 0 ? (
        <Text variant="secondary">
          {expectedGraderCount > 0
            ? "Scores will appear as graders finish."
            : "No scores for this run."}
        </Text>
      ) : (
        <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
          {scores.map((score) => {
            const open = expanded[score.id] ?? false;
            return (
              <li key={score.id} className="p-4">
                <button
                  type="button"
                  className="flex w-full items-start gap-2 text-left"
                  onClick={() => {
                    setExpanded((current) => ({
                      ...current,
                      [score.id]: !open,
                    }));
                  }}
                >
                  <Icon
                    icon={open ? ChevronDown : ChevronRight}
                    size="sm"
                    className="mt-0.5 shrink-0 text-muted-foreground"
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <Text
                        as="span"
                        variant="body"
                        className="text-[length:var(--ef-text-section)] font-semibold tabular-nums leading-none"
                      >
                        {score.value.numeric !== null
                          ? score.value.numeric.toFixed(2)
                          : formatScoreValue(score.value)}
                      </Text>
                      <Badge status={scoreResultBadge(score.value)}>
                        {score.value.passed === true
                          ? "PASS"
                          : score.value.passed === false
                            ? "FAIL"
                            : formatScoreValue(score.value)}
                      </Badge>
                    </div>
                    <Text
                      as="span"
                      variant="body"
                      className="font-medium font-mono text-[length:var(--ef-text-caption)]"
                    >
                      {truncateId(score.grader_id, 20)}
                    </Text>
                    <Text variant="caption" className="font-mono">
                      version {truncateId(score.grader_version_id, 16)}
                    </Text>
                  </div>
                </button>

                {open ? (
                  <div className="mt-3 ml-6 space-y-3 border-l border-border pl-4">
                    <ScoreField label="Result" value={formatScoreValue(score.value)} />
                    <ScoreField
                      label="Passed"
                      value={
                        score.value.passed === null ? "—" : score.value.passed ? "true" : "false"
                      }
                    />
                    <ScoreField
                      label="Numeric"
                      value={score.value.numeric === null ? "—" : String(score.value.numeric)}
                    />
                    <ScoreField label="Categorical" value={score.value.categorical ?? "—"} />
                    <ScoreField
                      label="Explanation artifact"
                      value={score.explanation_artifact_id ?? "None"}
                      mono
                    />
                    <ScoreField label="Score ID" value={score.id} mono />
                    <ScoreField label="Grader ID" value={score.grader_id} mono />
                    <ScoreField label="Grader version" value={score.grader_version_id} mono />
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {pending > 0
        ? Array.from({ length: pending }, (_, index) => (
            <div
              key={`pending-${String(index)}`}
              className="rounded-[var(--ef-radius-panel)] border border-dashed border-border px-4 py-3"
            >
              <Cluster gap={2} className="items-center">
                <Badge status="grading">Awaiting</Badge>
                <Text variant="secondary">Grader slot not yet reported</Text>
              </Cluster>
            </div>
          ))
        : null}
    </div>
  );
}

function ScoreField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Text as="div" variant="caption">
        {label}
      </Text>
      <Text
        as="div"
        variant="body"
        className={mono ? "break-all font-mono text-[length:var(--ef-text-caption)]" : undefined}
      >
        {value}
      </Text>
    </div>
  );
}
