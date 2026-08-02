"use client";

import { Toaster, TooltipProvider } from "@agent-eval/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import type { ReactNode } from "react";

import { OfflineBanner } from "@/components/patterns/offline-banner";
import { ThemeProvider } from "@/components/theme-provider";
import { PreferencesProvider } from "@/features/settings/preferences-provider";
import { AuthProvider } from "@/lib/auth/auth-provider";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={200}>
          <AuthProvider>
            <PreferencesProvider>
              <OfflineBanner />
              {children}
              <Toaster />
            </PreferencesProvider>
          </AuthProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
