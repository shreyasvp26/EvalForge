import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { ComingSoonState } from "@/components/patterns/coming-soon-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function RunsPage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/projects" }, { label: "Runs" }]} />
        }
        title="Runs"
        description="Execution history and run detail screens arrive with product CRUD."
      />
      <Section className="mt-8">
        <ComingSoonState
          featureLabel="Runs"
          description="Navigation and shortcuts (G then R) are live. Listing and inspecting runs is out of scope for Phase 15B."
        />
      </Section>
    </PageLayout>
  );
}
