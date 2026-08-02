import { Play } from "@agent-eval/ui";

import { EmptyContent } from "@/components/layouts/empty-content";
import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";

export default function RunsPage() {
  return (
    <PageLayout>
      <PageHeader title="Runs" description="Placeholder route for the product hierarchy shell." />
      <Section className="mt-8">
        <EmptyContent
          fill
          icon={Play}
          title="Runs come next"
          description="No CRUD in Phase 15B — this route uses the shared product layout system."
        />
      </Section>
    </PageLayout>
  );
}
