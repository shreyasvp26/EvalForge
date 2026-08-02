import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { ComingSoonState } from "@/components/patterns/coming-soon-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function SuitesPage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/" }, { label: "Suites" }]} />
        }
        title="Suites"
        description="Suite management arrives with product CRUD."
      />
      <Section className="mt-8">
        <ComingSoonState
          featureLabel="Suites"
          description="Navigation is live. Creating and managing suites is out of scope for Phase 15B."
        />
      </Section>
    </PageLayout>
  );
}
