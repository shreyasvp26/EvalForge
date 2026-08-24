"use client";

import { Text, cn } from "@agent-eval/ui";
import Link from "next/link";

import type { EvaluationHealth } from "./utils";

function HealthStat({
  label,
  value,
  href,
  tone = "neutral",
}: {
  label: string;
  value: string;
  href: string;
  tone?: "neutral" | "running" | "success" | "danger";
}) {
  const toneClass =
    tone === "running"
      ? "text-running"
      : tone === "success"
        ? "text-success"
        : tone === "danger"
          ? "text-danger"
          : "text-foreground";

  return (
    <Link
      href={href}
      className="group min-w-0 rounded-[var(--ef-radius-control)] px-3 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-4"
    >
      <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.12em]">
        {label}
      </Text>
      <Text
        as="div"
        variant="body"
        className={cn(
          "mt-1 text-[length:var(--ef-text-page)] font-semibold leading-none tabular-nums",
          toneClass,
        )}
      >
        {value}
      </Text>
    </Link>
  );
}

/**
 * Evaluation-centric health strip derived from sampled recent runs — not global KPIs.
 */
export function EvaluationHealthStrip({ health }: { health: EvaluationHealth }) {
  const passRate =
    health.terminal > 0 ? `${String(Math.round((health.passed / health.terminal) * 100))}%` : "—";

  return (
    <section
      aria-label="Evaluation health"
      className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <Text as="div" variant="body" className="font-medium">
            Evaluation health
          </Text>
          <Text as="p" variant="caption" className="mt-0.5">
            From {String(health.sampledRuns)} recent run
            {health.sampledRuns === 1 ? "" : "s"} across sampled projects
          </Text>
        </div>
        <Link
          href="/runs"
          className="text-[length:var(--ef-text-caption)] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Open runs
        </Link>
      </div>
      <div className="grid grid-cols-2 divide-border sm:grid-cols-4 sm:divide-x">
        <HealthStat
          label="Active"
          value={String(health.active)}
          href="/runs"
          tone={health.active > 0 ? "running" : "neutral"}
        />
        <HealthStat label="Pass rate" value={passRate} href="/runs" tone="success" />
        <HealthStat label="Passed" value={String(health.passed)} href="/runs" tone="success" />
        <HealthStat
          label="Failures"
          value={String(health.failed)}
          href="/runs"
          tone={health.failed > 0 ? "danger" : "neutral"}
        />
      </div>
    </section>
  );
}
