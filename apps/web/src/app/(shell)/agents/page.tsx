import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Section } from "@/components/layouts/section";
import { ComingSoonState } from "@/components/patterns/coming-soon-state";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export default function AgentsPage() {
  return (
    <PageLayout>
      <PageHeader
        breadcrumbs={
          <Breadcrumbs items={[{ label: "Workspace", href: "/projects" }, { label: "Agents" }]} />
        }
        title="Agents"
        description="Adapter and agent registry screens arrive in a later phase."
      />
      <Section className="mt-8">
        <ComingSoonState
          featureLabel="Agents"
          description="Navigation and shortcuts (G then A) are live. Managing agents and adapters is out of scope for Phase 15B."
        />
      </Section>
    </PageLayout>
  );
}
