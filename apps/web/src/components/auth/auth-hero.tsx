import { Text } from "@agent-eval/ui";

import { AuthFeatureGrid } from "@/components/auth/auth-feature-grid";

/** Left hero — product identity, headline, and feature grid. */
export function AuthHero() {
  return (
    <section className="flex flex-col justify-center py-6 sm:py-8 lg:py-10 xl:py-12">
      <div className="w-full max-w-2xl space-y-8 lg:max-w-none lg:pr-6 xl:pr-10">
        <div className="space-y-5 motion-safe:animate-[ef-fade-up_0.7s_ease-out_both]">
          <h1 className="text-[clamp(2.5rem,5vw,4.25rem)] font-semibold leading-[1.05] tracking-[-0.03em]">
            <span className="block text-foreground">Evaluate.</span>
            <span className="ef-auth-gradient-text block">Compare.</span>
            <span className="block text-foreground">Ship with Confidence.</span>
          </h1>
          <Text
            variant="secondary"
            className="max-w-lg text-[length:var(--ef-text-card)] leading-relaxed"
          >
            EvalForge is the modern platform for evaluating coding agents. Run, grade, and compare
            agent performance with precision and clarity.
          </Text>
        </div>

        <AuthFeatureGrid />
      </div>
    </section>
  );
}
