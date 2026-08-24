"use client";

import { ArrowRight, Bot, CheckCircle2, GitBranch, Icon, Text } from "@agent-eval/ui";

/** Left panel — product story + evaluation flow abstraction. */
export function AuthBrandPanel() {
  return (
    <div
      className="relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between"
      style={{ background: "var(--ef-auth-mesh)" }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60 motion-safe:animate-[ef-auth-drift_24s_ease-in-out_infinite]"
        style={{
          background:
            "radial-gradient(circle at 30% 40%, var(--ef-accent-glow) 0%, transparent 45%)",
        }}
      />

      <div className="relative z-10 flex flex-1 flex-col justify-center px-10 py-12 xl:px-14">
        <div className="space-y-6 motion-safe:animate-[ef-fade-up_0.6s_ease-out_both]">
          <div className="space-y-2">
            <Text variant="caption" className="font-mono tracking-[0.2em] uppercase text-accent">
              EvalForge
            </Text>
            <h1 className="max-w-md text-[length:var(--ef-text-display)] font-semibold leading-[var(--ef-text-display-leading)] tracking-tight text-foreground">
              Evaluate AI coding agents with confidence.
            </h1>
            <Text variant="secondary" className="max-w-md text-[length:var(--ef-text-body)]">
              Run agents in isolated environments, observe every execution, and measure outcomes
              with reproducible evaluations.
            </Text>
          </div>

          <ExecutionFlowVisual />
        </div>
      </div>

      <div className="relative z-10 border-t border-border/60 px-10 py-5 xl:px-14">
        <ul className="flex flex-wrap gap-x-6 gap-y-2">
          {["Agent execution", "Sandbox isolation", "Grader scoring", "Full traceability"].map(
            (item) => (
              <li key={item}>
                <Text variant="caption" className="text-muted-foreground">
                  {item}
                </Text>
              </li>
            ),
          )}
        </ul>
      </div>
    </div>
  );
}

function ExecutionFlowVisual() {
  const steps = [
    { label: "Case", icon: GitBranch, detail: "Prompt + spec" },
    { label: "Agent", icon: Bot, detail: "Adapter run" },
    { label: "Score", icon: CheckCircle2, detail: "Grader outcome" },
  ];

  return (
    <div
      aria-hidden
      className="relative max-w-sm rounded-[var(--ef-radius-panel)] border border-border/80 bg-card/60 p-5 shadow-ef-md backdrop-blur-sm motion-safe:animate-[ef-fade-up_0.7s_ease-out_0.15s_both]"
    >
      <Text
        variant="caption"
        className="font-mono uppercase tracking-[0.12em] text-muted-foreground"
      >
        Evaluation pipeline
      </Text>
      <ol className="mt-4 space-y-0">
        {steps.map((step, index) => (
          <li key={step.label} className="relative flex items-start gap-3 pb-4 last:pb-0">
            {index < steps.length - 1 ? (
              <span className="absolute left-[15px] top-8 h-[calc(100%-12px)] w-px bg-border" />
            ) : null}
            <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] border border-border bg-muted/80">
              <Icon icon={step.icon} size="sm" className="text-accent" aria-hidden />
            </span>
            <div className="min-w-0 pt-0.5">
              <Text as="div" variant="body" className="font-medium">
                {step.label}
              </Text>
              <Text variant="caption" className="text-muted-foreground">
                {step.detail}
              </Text>
            </div>
            {index < steps.length - 1 ? (
              <Icon
                icon={ArrowRight}
                size="xs"
                className="absolute -bottom-1 left-[11px] text-muted-foreground/60"
                aria-hidden
              />
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
