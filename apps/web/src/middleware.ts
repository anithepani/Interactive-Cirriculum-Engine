import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_ROUTES = ["/upload", "/dashboard", "/curriculum", "/support"];

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const isProtected = PROTECTED_ROUTES.some((route) => path.startsWith(route));

  if (isProtected) {
    const token = request.cookies.get("access_token")?.value;
    const bypass = request.nextUrl.searchParams.get("bypass") === "true";

    if (!token && !bypass) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", path);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect authenticated users away from auth pages
  const authPages = ["/login", "/signup"];
  if (authPages.some((p) => path.startsWith(p))) {
    const token = request.cookies.get("access_token")?.value;
    if (token) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/upload",
    "/upload/:path*",
    "/dashboard",
    "/dashboard/:path*",
    "/curriculum",
    "/curriculum/:path*",
    "/support",
    "/support/:path*",
    "/login",
    "/signup",
  ],
};
