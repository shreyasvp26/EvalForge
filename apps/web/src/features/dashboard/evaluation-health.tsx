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
    primary: {
      icon: "bg-[var(--ef-accent-muted)] text-[var(--ef-accent)]",
      glow: "group-hover:shadow-[0_0_24px_var(--ef-accent-glow)]",
    },
    success: {
      icon: "bg-success-muted text-success",
      glow: "group-hover:shadow-[0_0_20px_rgb(15_122_69/0.15)]",
    },
    running: {
      icon: "bg-running-muted text-running",
      glow: "group-hover:shadow-[0_0_20px_rgb(47_95_158/0.15)]",
    },
    danger: {
      icon: "bg-danger-muted text-danger",
      glow: "group-hover:shadow-[0_0_20px_rgb(180_35_24/0.12)]",
    },
  } as const;

  return (
    <Link
      href={href}
      className={cn(
        "group relative overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm transition-[border-color,box-shadow,transform] duration-[var(--ef-duration-fast)] hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-5",
        toneStyles[tone].glow,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full opacity-40 blur-2xl"
        style={{
          background:
            tone === "primary"
              ? "var(--ef-accent-glow)"
              : tone === "success"
                ? "rgb(15 122 69 / 0.2)"
                : tone === "running"
                  ? "rgb(47 95 158 / 0.2)"
                  : "rgb(180 35 24 / 0.18)",
        }}
      />
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-3">
          <Text
            as="div"
            variant="caption"
            className="font-mono uppercase tracking-[0.12em] text-muted-foreground"
          >
            {label}
          </Text>
          <Text
            as="div"
            className="text-[clamp(1.75rem,2.5vw,2.25rem)] font-semibold leading-none tracking-tight tabular-nums text-foreground"
          >
            {value}
          </Text>
          <Text as="p" variant="caption" className="text-muted-foreground">
            {context}
          </Text>
        </div>
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
            toneStyles[tone].icon,
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
    <section aria-label="Evaluation health" className="space-y-3">
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
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
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
