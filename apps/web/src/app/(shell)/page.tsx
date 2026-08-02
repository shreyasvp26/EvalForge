import { EmptyState, FolderKanban, Heading, Stack, Text } from "@agent-eval/ui";

export default function HomePage() {
  return (
    <Stack gap={5} className="mx-auto max-w-3xl px-6 py-10">
      <Stack gap={2}>
        <Text variant="caption" className="font-mono uppercase tracking-wide">
          Workspace
        </Text>
        <Heading variant="page">Projects</Heading>
        <Text variant="secondary">
          Phase 15A foundation. Navigation hierarchy is live; project CRUD arrives in a later phase.
        </Text>
      </Stack>
      <EmptyState
        icon={FolderKanban}
        title="No projects yet"
        description="The shell is ready. Create and manage projects once product screens land."
      />
    </Stack>
  );
}
