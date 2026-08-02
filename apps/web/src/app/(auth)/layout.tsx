import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-dvh flex-col bg-background text-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--ef-color-muted)_0%,_transparent_55%)] opacity-70"
      />
      <div className="relative z-10 flex flex-1 flex-col">{children}</div>
    </div>
  );
}
