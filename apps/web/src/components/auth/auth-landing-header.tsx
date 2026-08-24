import { Text } from "@agent-eval/ui";

import { AuthBrandLockup } from "@/components/auth/auth-brand-lockup";
import { ThemeToggle } from "@/components/theme-toggle";

/** Top bar — brand lockup, tagline, theme toggle. */
export function AuthLandingHeader() {
  return (
    <header className="relative z-20 flex items-center justify-between gap-4 py-5 lg:py-6">
      <AuthBrandLockup />
      <div className="flex items-center gap-3 sm:gap-4">
        <Text variant="caption" className="hidden text-muted-foreground sm:inline">
          Built for developers
        </Text>
        <ThemeToggle />
      </div>
    </header>
  );
}
