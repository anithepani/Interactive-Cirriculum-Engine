import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Navigation gating only. The API remains the authority on authorization: it
 * validates the `Authorization: Bearer` token on every request. Middleware just
 * avoids rendering an app shell for a visitor with no session.
 *
 * The `access_token` cookie read here is set server-side by /auth/session.
 */
const PROTECTED_ROUTES = [
  "/upload",
  "/dashboard",
  "/curriculum",
  "/curricula",
  "/support",
  "/progress",
  "/settings",
  "/exercises",
  "/quiz",
  "/reader",
  "/discover",
];

const AUTH_ROUTES = ["/login", "/signup"];

/**
 * Exact segment match. Plain `startsWith` would also protect a future public
 * route such as `/uploads-guide`, and would miss nothing useful in return.
 */
function matchesRoute(path: string, routes: string[]): boolean {
  return routes.some((route) => path === route || path.startsWith(`${route}/`));
}

/**
 * Reject a token whose `exp` has already passed. The signature is not verified
 * here (that is the API's job); this only avoids a pointless render for a
 * session we already know is dead.
 */
function isExpired(token: string): boolean {
  const parts = token.split(".");
  if (parts.length !== 3) return true;

  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload.padEnd(
      payload.length + ((4 - (payload.length % 4)) % 4),
      "="
    );
    const claims = JSON.parse(atob(padded));
    if (typeof claims?.exp !== "number") return false;
    return claims.exp * 1000 <= Date.now();
  } catch {
    // Unparseable payloads are treated as unusable rather than trusted.
    return true;
  }
}

function hasSession(request: NextRequest): boolean {
  const access = request.cookies.get("access_token")?.value;
  if (access && !isExpired(access)) return true;

  // The access cookie is short-lived (1h, matching the JWT), but the refresh
  // cookie lasts 7 days. Without this fallback a user returning after an hour
  // would be bounced to /login despite holding a perfectly good refresh token.
  // Letting the navigation through lets authFetch rotate the access token and
  // re-sync the cookie; the API still authorizes every request either way.
  const refresh = request.cookies.get("refresh_token")?.value;
  return Boolean(refresh) && !isExpired(refresh as string);
}

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const authenticated = hasSession(request);

  if (matchesRoute(path, PROTECTED_ROUTES) && !authenticated) {
    const loginUrl = new URL("/login", request.url);
    // Preserve the query string so the user resumes exactly where they aimed.
    loginUrl.searchParams.set("redirect", `${path}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  // Keep signed-in users off the login/signup forms.
  if (matchesRoute(path, AUTH_ROUTES) && authenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Bare paths are listed alongside the `:path*` forms explicitly rather than
  // relying on the wildcard matching zero segments.
  matcher: [
    "/upload",
    "/dashboard",
    "/curriculum",
    "/curricula",
    "/support",
    "/progress",
    "/settings",
    "/exercises",
    "/quiz",
    "/reader",
    "/discover",
    "/upload/:path*",
    "/dashboard/:path*",
    "/curriculum/:path*",
    "/curricula/:path*",
    "/support/:path*",
    "/progress/:path*",
    "/settings/:path*",
    "/exercises/:path*",
    "/quiz/:path*",
    "/reader/:path*",
    "/discover/:path*",
    "/login",
    "/signup",
  ],
};
