import type { ReactNode } from "react";

import { AuthHero } from "@/components/auth/auth-hero";
import { AuthLandingBackground } from "@/components/auth/auth-landing-background";
import { AuthLandingHeader } from "@/components/auth/auth-landing-header";

/** Shared horizontal bounds — keeps hero + auth card as one centered composition. */
const AUTH_SHELL = "mx-auto w-full max-w-7xl px-6 sm:px-8 md:px-10 lg:px-12 xl:px-14";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="ef-auth-landing relative min-h-dvh overflow-x-hidden">
      <AuthLandingBackground />

      <div className="relative z-10 flex min-h-dvh flex-col">
        <div className={`${AUTH_SHELL} shrink-0`}>
          <AuthLandingHeader />
        </div>

        <div className={`${AUTH_SHELL} flex flex-1 flex-col pb-12 lg:pb-16`}>
          <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(360px,420px)] lg:items-center lg:gap-x-14 xl:gap-x-20">
            <AuthHero />

            <div className="mt-10 flex flex-col justify-center lg:mt-0 lg:justify-self-end">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
