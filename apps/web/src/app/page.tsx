import { Heading, Text } from "@agent-eval/ui";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-4 px-6 py-16">
      <Text variant="caption" className="font-mono uppercase tracking-wide">
        EvalForge
      </Text>
      <Heading variant="page">Frontend foundation</Heading>
      <Text variant="secondary">
        Phase 15A bootstrap. Design tokens, typography, and theme are in place. The app shell and
        component library land next. Product CRUD remains out of scope.
      </Text>
    </main>
  );
}
