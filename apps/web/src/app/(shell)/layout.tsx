import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { RequireAuth } from "@/lib/auth/require-auth";

export default function ShellLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
