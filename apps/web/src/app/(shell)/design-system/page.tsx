import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Heading,
  Input,
  Stack,
  Text,
} from "@agent-eval/ui";
import Link from "next/link";

import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Design system",
};

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-8 space-y-4 border-t border-border pt-10">
      <Stack gap={1}>
        <Heading variant="section" level={2}>
          {title}
        </Heading>
        <Text variant="secondary">{description}</Text>
      </Stack>
      {children}
    </section>
  );
}

function Swatch({ name, className }: { name: string; className: string }) {
  return (
    <div className="space-y-2">
      <div className={`h-14 rounded-[var(--ef-radius-panel)] border border-border ${className}`} />
      <Text variant="caption" className="font-mono">
        {name}
      </Text>
    </div>
  );
}

export default function DesignSystemPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Stack gap={3} className="pb-8">
        <Text variant="caption" className="font-mono uppercase tracking-wide">
          Product gallery
        </Text>
        <Heading variant="page">Design system</Heading>
        <Text variant="secondary">
          Curated reference inside the real EvalForge shell. Exhaustive component variants live in
          Storybook (`pnpm --filter @agent-eval/ui storybook`). Principles:{" "}
          <Link
            href="https://github.com/shreyasvp26/EvalForge/blob/main/docs/design/design-principles.md"
            className="text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            docs/design/design-principles.md
          </Link>
          .
        </Text>
      </Stack>

      <nav aria-label="Design system sections" className="mb-2 flex flex-wrap gap-3">
        {(
          [
            ["principles", "Principles"],
            ["color", "Color"],
            ["type", "Typography"],
            ["components", "Components"],
            ["keyboard", "Keyboard"],
            ["anti", "Anti-patterns"],
          ] as const
        ).map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            className="text-[length:var(--ef-text-caption)] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {label}
          </a>
        ))}
      </nav>

      <Section
        id="principles"
        title="Principles"
        description="Minimal, calm, dense-not-cluttered. Typography and spacing do the work; accent color stays under ~10%."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            [
              "Hybrid ownership",
              "Tokens/primitives in @agent-eval/ui. Shell and domain UI in apps/web.",
            ],
            ["Keyboard-first", "⌘K palette, visible focus-visible, no focus traps without Escape."],
            ["Motion with meaning", "Only if it answers where-from, where-to, or what-changed."],
          ].map(([title, body]) => (
            <Card key={title}>
              <CardHeader>
                <Heading variant="card" level={3}>
                  {title}
                </Heading>
              </CardHeader>
              <CardContent>
                <Text variant="secondary">{body}</Text>
              </CardContent>
            </Card>
          ))}
        </div>
      </Section>

      <Section
        id="color"
        title="Color"
        description="Neutral-first surfaces with calm blue-gray accent and quiet semantic status tokens."
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Swatch name="background" className="bg-background" />
          <Swatch name="card" className="bg-card" />
          <Swatch name="muted" className="bg-muted" />
          <Swatch name="accent" className="bg-accent" />
          <Swatch name="success" className="bg-success-muted" />
          <Swatch name="warning" className="bg-warning-muted" />
          <Swatch name="danger" className="bg-danger-muted" />
          <Swatch name="running" className="bg-running-muted" />
        </div>
        <div className="flex flex-wrap gap-2 pt-2">
          <Badge status="queued">Queued</Badge>
          <Badge status="running">Running</Badge>
          <Badge status="grading">Grading</Badge>
          <Badge status="completed">Completed</Badge>
          <Badge status="danger">Failed</Badge>
          <Badge status="cancelled">Cancelled</Badge>
        </div>
      </Section>

      <Section
        id="type"
        title="Typography"
        description="Use Heading and Text only — never ad-hoc text-lg or raw product headings."
      >
        <Stack gap={3}>
          <Heading variant="display">Display</Heading>
          <Heading variant="page">Page title</Heading>
          <Heading variant="section" level={2}>
            Section title
          </Heading>
          <Heading variant="card" level={3}>
            Card title
          </Heading>
          <Text variant="body">Body — default reading text for product content.</Text>
          <Text variant="secondary">Secondary — supporting copy with quieter contrast.</Text>
          <Text variant="caption">Caption — metadata and helper text.</Text>
          <Text variant="code">run_01HZX9K…</Text>
          <Text variant="table">Table label</Text>
        </Stack>
      </Section>

      <Section
        id="components"
        title="Components"
        description="Representative primitives. Full matrices and a11y checks are in Storybook."
      >
        <Stack gap={4}>
          <div className="flex flex-wrap gap-2">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button loading>Loading</Button>
          </div>
          <Input
            aria-label="Example input"
            placeholder="Quiet control, 8px radius"
            className="max-w-sm"
          />
        </Stack>
      </Section>

      <Section
        id="keyboard"
        title="Keyboard"
        description="Treat the keyboard as a first-class input device."
      >
        <ul className="space-y-2">
          <li>
            <Text as="span" variant="code">
              ⌘K / Ctrl+K
            </Text>
            <Text as="span" variant="secondary">
              {" "}
              — Open command palette
            </Text>
          </li>
          <li>
            <Text as="span" variant="code">
              Esc
            </Text>
            <Text as="span" variant="secondary">
              {" "}
              — Close overlays
            </Text>
          </li>
          <li>
            <Text as="span" variant="code">
              Tab
            </Text>
            <Text as="span" variant="secondary">
              {" "}
              — Move focus with a visible ring
            </Text>
          </li>
        </ul>
      </Section>

      <Section
        id="anti"
        title="Anti-patterns"
        description="If a PR ships any of these, send it back."
      >
        <ul className="list-disc space-y-2 pl-5 text-[length:var(--ef-text-body)] text-muted-foreground">
          <li>Glassmorphism, neon AI gradients, oversized radii, floating card grids</li>
          <li>Direct lucide-react imports or raw h1/p styling in apps/web</li>
          <li>Domain components (RunCard, ScorePanel, …) inside packages/ui</li>
          <li>Decorative charts or springy motion with no spatial meaning</li>
        </ul>
      </Section>
    </div>
  );
}
