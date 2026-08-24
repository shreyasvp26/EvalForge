import {
  BarChart3,
  Code2,
  FlaskConical,
  GitCompare,
  Icon,
  Play,
  Terminal,
  Text,
} from "@agent-eval/ui";

import type { LucideIcon } from "@agent-eval/ui";

const features: { title: string; description: string; icon: LucideIcon; delay: string }[] = [
  {
    title: "Run evaluations",
    description: "Execute coding-agent tasks.",
    icon: Play,
    delay: "0.1s",
  },
  {
    title: "Track results",
    description: "Real-time evaluation insights.",
    icon: BarChart3,
    delay: "0.15s",
  },
  {
    title: "Inspect execution",
    description: "Deep visibility into agent behavior.",
    icon: Terminal,
    delay: "0.2s",
  },
  {
    title: "Compare agents",
    description: "Understand performance differences.",
    icon: GitCompare,
    delay: "0.25s",
  },
  {
    title: "Grade outcomes",
    description: "Reproducible scoring pipelines.",
    icon: FlaskConical,
    delay: "0.3s",
  },
  {
    title: "Built for developers",
    description: "Open, extensible, powerful.",
    icon: Code2,
    delay: "0.35s",
  },
];

export function AuthFeatureGrid() {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {features.map((feature) => (
        <li
          key={feature.title}
          className="motion-safe:animate-[ef-fade-up_0.8s_ease-out_both]"
          style={{ animationDelay: feature.delay }}
        >
          <div className="flex gap-3">
            <span
              aria-hidden
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] border border-[var(--ef-auth-feature-border)] bg-[var(--ef-auth-feature-bg)]"
            >
              <Icon icon={feature.icon} size="sm" className="text-[var(--ef-auth-primary)]" />
            </span>
            <div className="min-w-0 space-y-0.5">
              <Text as="div" variant="body" className="font-medium text-foreground">
                {feature.title}
              </Text>
              <Text variant="caption" className="text-muted-foreground">
                {feature.description}
              </Text>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
