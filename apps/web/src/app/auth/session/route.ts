/**
 * Same-origin session boundary — /auth/session
 * --------------------------------------------
 * Next.js middleware runs on the edge and can only read cookies; it cannot see
 * `localStorage`. Previously the browser copied its tokens into cookies with
 * `document.cookie`, so login could succeed client-side while middleware saw no
 * cookie and bounced every protected navigation back to /login.
 *
 * This route makes the middleware-visible cookie authoritative and server-set:
 *   POST   validates the access token against the API, then sets HttpOnly cookies
 *   DELETE expires both cookies (logout)
 *
 * The API itself still authenticates via the `Authorization: Bearer` header, so
 * `authFetch` keeps using the access token from localStorage. This route only
 * owns the navigation-gating cookies.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCESS_TOKEN_COOKIE = "access_token";
const REFRESH_TOKEN_COOKIE = "refresh_token";

/** Fallback lifetimes used when a token carries no usable `exp` claim. */
const ACCESS_FALLBACK_MAX_AGE = 60 * 60; // 1 hour, matches JWT_ACCESS_TTL_MIN
const REFRESH_FALLBACK_MAX_AGE = 60 * 60 * 24 * 7; // 7 days, matches JWT_REFRESH_TTL_DAYS
const MIN_MAX_AGE = 30;

/** Server-only API base. Never exposed to the browser. */
function apiBase(): string {
  return process.env.API_URL || "http://localhost:8000";
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Read the `exp` claim without verifying the signature. The token is separately
 * validated against the API before any cookie is written, so this is only used
 * to align cookie lifetime with token lifetime.
 */
export function tokenMaxAge(token: string, fallbackSeconds: number): number {
  const parts = token.split(".");
  if (parts.length !== 3) return fallbackSeconds;

  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
    const claims = JSON.parse(Buffer.from(padded, "base64").toString("utf8"));
    const exp = typeof claims?.exp === "number" ? claims.exp : null;
    if (exp === null) return fallbackSeconds;

    const remaining = Math.floor(exp - Date.now() / 1000);
    if (!Number.isFinite(remaining) || remaining <= 0) return 0;
    return Math.min(remaining, fallbackSeconds);
  } catch {
    return fallbackSeconds;
  }
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: isProduction(),
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const accessToken = (body as { access_token?: unknown })?.access_token;
  const refreshToken = (body as { refresh_token?: unknown })?.refresh_token;

  if (typeof accessToken !== "string" || accessToken.length === 0) {
    return NextResponse.json({ error: "access_token is required" }, { status: 400 });
  }
  if (refreshToken !== undefined && typeof refreshToken !== "string") {
    return NextResponse.json({ error: "refresh_token must be a string" }, { status: 400 });
  }

  // Only mint a session for a token the API actually accepts. This stops a
  // forged or expired value from being installed as a middleware pass.
  let verified: Response;
  try {
    verified = await fetch(`${apiBase()}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ error: "Authentication service unreachable" }, { status: 502 });
  }

  if (!verified.ok) {
    return NextResponse.json({ error: "Invalid access token" }, { status: 401 });
  }

  const accessMaxAge = tokenMaxAge(accessToken, ACCESS_FALLBACK_MAX_AGE);
  if (accessMaxAge < MIN_MAX_AGE) {
    return NextResponse.json({ error: "Access token already expired" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ACCESS_TOKEN_COOKIE, accessToken, cookieOptions(accessMaxAge));

  if (typeof refreshToken === "string" && refreshToken.length > 0) {
    const refreshMaxAge = tokenMaxAge(refreshToken, REFRESH_FALLBACK_MAX_AGE);
    if (refreshMaxAge >= MIN_MAX_AGE) {
      response.cookies.set(REFRESH_TOKEN_COOKIE, refreshToken, cookieOptions(refreshMaxAge));
    }
  }

  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  for (const name of [ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE]) {
    response.cookies.set(name, "", cookieOptions(0));
  }
  return response;
}
