import type { ReactNode } from "react";

import { AuthHero } from "@/components/auth/auth-hero";
import { AuthLandingBackground } from "@/components/auth/auth-landing-background";
import { AuthLandingHeader } from "@/components/auth/auth-landing-header";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="ef-auth-landing relative min-h-dvh overflow-x-hidden">
      <AuthLandingBackground />

      <div className="relative z-10 flex min-h-dvh flex-col">
        <AuthLandingHeader />

        <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(380px,440px)] lg:items-stretch xl:grid-cols-[minmax(0,1.2fr)_440px]">
          <AuthHero />

          <div className="flex flex-1 flex-col justify-center px-6 pb-12 sm:px-10 lg:px-8 lg:pb-0 xl:px-10 xl:pr-16">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
