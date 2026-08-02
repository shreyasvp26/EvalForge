import { EmptyState, Heading, Layers, Stack, Text } from "@agent-eval/ui";

export default function SuitesPage() {
  return (
    <Stack gap={5} className="mx-auto max-w-3xl px-6 py-10">
      <Stack gap={2}>
        <Heading variant="page">Suites</Heading>
        <Text variant="secondary">Placeholder route for the product hierarchy shell.</Text>
      </Stack>
      <EmptyState
        icon={Layers}
        title="Suites come next"
        description="No CRUD in Phase 15A — this route exists for navigation and command palette destinations."
      />
    </Stack>
  );
}
