import { Layers } from "@agent-eval/ui";

import { EmptyContent } from "@/components/layouts/empty-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function SuitesPage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/" }, { label: "Suites" }]} />
        }
        title="Suites"
        description="Placeholder route for the product hierarchy shell."
      />
      <Section className="mt-8">
        <EmptyContent
          fill
          icon={Layers}
          title="Suites come next"
          description="No CRUD in Phase 15B — this route uses the shared product layout system."
        />
      </Section>
    </PageLayout>
  );
}
