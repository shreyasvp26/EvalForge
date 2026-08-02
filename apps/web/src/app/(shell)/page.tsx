import { FolderKanban } from "@agent-eval/ui";

import { EmptyContent } from "@/components/layouts/empty-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function HomePage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/" }, { label: "Projects" }]} />
        }
        eyebrow="Workspace"
        title="Projects"
        description="Phase 15B product layouts and navigation are live. Project CRUD arrives in a later phase."
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
