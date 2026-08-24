import type { ReactNode } from "react";

import { AuthBrandPanel } from "@/components/auth/auth-brand-panel";
import { ThemeToggle } from "@/components/theme-toggle";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative grid min-h-dvh bg-background text-foreground lg:grid-cols-2">
      <AuthBrandPanel />

      <div className="relative flex min-h-dvh flex-col">
        <div className="absolute right-4 top-4 z-20 sm:right-6 sm:top-6">
          <ThemeToggle />
        </div>

        {/* Mobile brand strip */}
        <div
          className="border-b border-border px-6 py-8 lg:hidden"
          style={{ background: "var(--ef-auth-mesh)" }}
        >
          <p className="font-mono text-[length:var(--ef-text-caption)] tracking-[0.16em] uppercase text-accent">
            EvalForge
          </p>
          <h1 className="mt-2 text-[length:var(--ef-text-section)] font-semibold leading-tight">
            Evaluation control plane
          </h1>
        </div>

        <div className="relative z-10 flex flex-1 flex-col">{children}</div>
      </div>
    </div>
  );
}
