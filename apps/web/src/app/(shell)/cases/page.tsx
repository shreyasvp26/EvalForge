import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { ComingSoonState } from "@/components/patterns/coming-soon-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function CasesPage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/projects" }, { label: "Cases" }]} />
        }
        title="Cases"
        description="Evaluation case authoring arrives with product CRUD."
      />
      <Section className="mt-8">
        <ComingSoonState
          featureLabel="Cases"
          description="Navigation is live. Creating and editing cases is out of scope for Phase 15B."
        />
      </Section>
    </PageLayout>
  );
}
