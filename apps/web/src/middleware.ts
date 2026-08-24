import { NextResponse } from "next/server";

import type { NextRequest } from "next/server";

import { hasSessionCookie } from "@/lib/auth/session";

const PUBLIC_PREFIXES = ["/login", "/_next", "/favicon.ico"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes (including /login) always pass. Do not redirect away from
  // /login based on the presence cookie — that cookie can outlive the JWT and
  // would loop with RequireAuth ("Redirecting to sign in" on a dark overlay).
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!hasSessionCookie(request.headers.get("cookie"))) {
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") {
      loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\..*).*)"],
};
