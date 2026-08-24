"use client";

import { AlertTriangle, CheckCircle2, Icon, Loader2, Text, cn } from "@agent-eval/ui";
import Link from "next/link";

import type { EvaluationHealth } from "./utils";
import type { LucideIcon } from "@agent-eval/ui";

function HealthStat({
  label,
  value,
  href,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: string;
  href: string;
  icon: LucideIcon;
  tone?: "neutral" | "running" | "success" | "danger";
}) {
  const toneStyles = {
    neutral: "text-foreground bg-muted/50",
    running: "text-running bg-running-muted",
    success: "text-success bg-success-muted",
    danger: "text-danger bg-danger-muted",
  };

  return (
    <Link
      href={href}
      className="group flex min-w-0 items-center gap-3 rounded-[var(--ef-radius-control)] px-4 py-4 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-5"
    >
      <span
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
          toneStyles[tone],
        )}
      >
        <Icon icon={icon} size="sm" aria-hidden />
      </span>
      <div className="min-w-0">
        <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.1em]">
          {label}
        </Text>
        <Text
          as="div"
          variant="body"
          className="mt-0.5 text-[length:var(--ef-text-page)] font-semibold leading-none tabular-nums"
        >
          {value}
        </Text>
      </div>
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
      className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card shadow-ef-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/20 px-4 py-3 sm:px-5">
        <div>
          <Text as="div" variant="body" className="font-medium">
            Evaluation health
          </Text>
          <Text as="p" variant="caption" className="mt-0.5 text-muted-foreground">
            {health.sampledRuns === 1
              ? "Sampled from 1 recent run across projects"
              : `Sampled from ${String(health.sampledRuns)} recent runs across projects`}
          </Text>
        </div>
        <Link
          href="/runs"
          className="rounded-[var(--ef-radius-control)] px-2 py-1 text-[length:var(--ef-text-caption)] text-muted-foreground underline-offset-2 transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Open runs
        </Link>
      </div>
      <div className="grid grid-cols-2 divide-y divide-border sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <HealthStat
          label="Active"
          value={String(health.active)}
          href="/runs"
          icon={Loader2}
          tone={health.active > 0 ? "running" : "neutral"}
        />
        <HealthStat
          label="Pass rate"
          value={passRate}
          href="/runs"
          icon={CheckCircle2}
          tone="success"
        />
        <HealthStat
          label="Passed"
          value={String(health.passed)}
          href="/runs"
          icon={CheckCircle2}
          tone="success"
        />
        <HealthStat
          label="Failures"
          value={String(health.failed)}
          href="/runs"
          icon={AlertTriangle}
          tone={health.failed > 0 ? "danger" : "neutral"}
        />
      </div>
    </section>
  );
}
