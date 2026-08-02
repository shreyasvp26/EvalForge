import { FolderKanban } from "@agent-eval/ui";

import { EmptyContent } from "@/components/layouts/empty-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";

export default function HomePage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="Workspace"
        title="Projects"
        description="Phase 15B product layouts are live. Project CRUD arrives in a later phase."
      />
      <Section className="mt-8">
        <EmptyContent
          fill
          icon={FolderKanban}
          title="No projects yet"
          description="The product layout system is ready. Create and manage projects once product screens land."
        />
      </Section>
    </PageLayout>
  );
}
