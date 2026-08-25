"use client";

import { AlertTriangle, CheckCircle2, Icon, Layers, Loader2, Text, cn } from "@agent-eval/ui";
import Link from "next/link";

import type { EvaluationHealth } from "./utils";
import type { LucideIcon } from "@agent-eval/ui";

function MetricCard({
  label,
  value,
  context,
  href,
  icon,
  tone = "primary",
}: {
  label: string;
  value: string;
  context: string;
  href: string;
  icon: LucideIcon;
  tone?: "primary" | "success" | "running" | "danger";
}) {
  const toneStyles = {
    primary: "bg-[var(--ef-accent-muted)] text-[var(--ef-accent)]",
    success: "bg-success-muted text-success",
    running: "bg-running-muted text-running",
    danger: "bg-danger-muted text-danger",
  } as const;

  return (
    <Link
      href={href}
      className="group rounded-[var(--ef-radius-panel)] border border-border bg-card px-3.5 py-3 shadow-ef-sm transition-[border-color,background-color] duration-[var(--ef-duration-fast)] hover:border-border-strong hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1.5">
          <Text
            as="div"
            variant="caption"
            className="font-mono uppercase tracking-[0.1em] text-muted-foreground"
          >
            {label}
          </Text>
          <Text
            as="div"
            className="text-[length:var(--ef-text-page)] font-semibold leading-none tracking-tight tabular-nums text-foreground sm:text-[1.5rem]"
          >
            {value}
          </Text>
          <Text as="p" variant="caption" className="line-clamp-1 text-muted-foreground">
            {context}
          </Text>
        </div>
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
            toneStyles[tone],
          )}
        >
          <Icon icon={icon} size="sm" aria-hidden />
        </span>
      </div>
    </Link>
  );
}

/**
 * Metric cards derived from sampled recent runs — labeled honestly, not global KPIs.
 */
export function EvaluationHealthStrip({ health }: { health: EvaluationHealth }) {
  const passRate =
    health.terminal > 0 ? `${String(Math.round((health.passed / health.terminal) * 100))}%` : "—";

  const sampleContext =
    health.sampledRuns === 1
      ? "From 1 recent sampled run"
      : `From ${String(health.sampledRuns)} recent sampled runs`;

  return (
    <section aria-label="Evaluation health" className="space-y-2.5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <Text as="div" variant="body" className="font-medium text-foreground">
            Evaluation health
          </Text>
          <Text as="p" variant="caption" className="mt-0.5 text-muted-foreground">
            Sampled across recent projects — not a global inventory.
          </Text>
        </div>
        <Link
          href="/runs"
          className="rounded-[var(--ef-radius-control)] px-2 py-1 text-[length:var(--ef-text-caption)] font-medium text-[var(--ef-accent)] underline-offset-2 transition-colors hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Open runs
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4 lg:gap-3">
        <MetricCard
          label="Recent runs"
          value={String(health.sampledRuns)}
          context={sampleContext}
          href="/runs"
          icon={Layers}
          tone="primary"
        />
        <MetricCard
          label="Pass rate"
          value={passRate}
          context={
            health.terminal > 0
              ? `${String(health.passed)} passed of ${String(health.terminal)} terminal`
              : "No terminal runs in sample"
          }
          href="/runs"
          icon={CheckCircle2}
          tone="success"
        />
        <MetricCard
          label="Active executions"
          value={String(health.active)}
          context={health.active > 0 ? "Queued, running, or grading" : "Nothing running now"}
          href="/runs"
          icon={Loader2}
          tone="running"
        />
        <MetricCard
          label="Failures"
          value={String(health.failed)}
          context={health.failed > 0 ? "Failed or failing scores" : "No failures in sample"}
          href="/runs"
          icon={AlertTriangle}
          tone={health.failed > 0 ? "danger" : "primary"}
        />
      </div>
    </section>
  );
}
