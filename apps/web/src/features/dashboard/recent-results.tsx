"use client";

import { Badge, Text } from "@agent-eval/ui";
import Link from "next/link";

import {
  formatDashboardDate,
  formatScoreValue,
  scoreOutcomeBadge,
  scoreOutcomeLabel,
  truncateId,
} from "./utils";

import type { DashboardScoreRow } from "./utils";

export function RecentResults({ results }: { results: DashboardScoreRow[] }) {
  if (results.length === 0) {
    return <Text variant="secondary">No scores yet. Launch a run to see results here.</Text>;
  }

  return (
    <ul className="divide-y divide-border border-y border-border">
      {results.map(({ score, run, projectName, outcome }) => (
        <li key={score.id}>
          <Link
            href={`/runs/${run.id}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Badge status={scoreOutcomeBadge(outcome)}>{scoreOutcomeLabel(outcome)}</Badge>
            <Text as="span" variant="body">
              {formatScoreValue(score.value)}
            </Text>
            <Text
              as="span"
              variant="caption"
              className="font-mono text-[length:var(--ef-text-caption)]"
            >
              {truncateId(score.grader_id, 12)}
            </Text>
            <Text as="span" variant="caption" className="min-w-0 truncate">
              {projectName}
            </Text>
            <Text as="span" variant="caption" className="ml-auto tabular-nums">
              {formatDashboardDate(run.created_at)}
            </Text>
          </Link>
        </li>
      ))}
    </ul>
  );
}
