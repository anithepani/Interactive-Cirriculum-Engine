import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

const HOST = "https://app.test";

/** Unsigned JWT-shaped token; middleware only reads `exp`. */
function jwt(expSecondsFromNow: number | null): string {
  const claims: Record<string, unknown> = { sub: "user-1" };
  if (expSecondsFromNow !== null) {
    claims.exp = Math.floor(Date.now() / 1000) + expSecondsFromNow;
  }
  const b64 = (o: unknown) =>
    Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(claims)}.sig`;
}

function request(
  path: string,
  token?: string,
  refresh?: string
): NextRequest {
  const req = new NextRequest(`${HOST}${path}`);
  if (token !== undefined) req.cookies.set("access_token", token);
  if (refresh !== undefined) req.cookies.set("refresh_token", refresh);
  return req;
}

/** Location header as a URL, or null when the response is a pass-through. */
function redirectTarget(res: Response): URL | null {
  const location = res.headers.get("location");
  return location ? new URL(location) : null;
}

const PROTECTED = [
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

describe("middleware: unauthenticated access", () => {
  it.each(PROTECTED)("redirects %s to login with no cookie", (path) => {
    const target = redirectTarget(middleware(request(path)));

    expect(target?.pathname).toBe("/login");
    expect(target?.searchParams.get("redirect")).toBe(path);
  });

  it("redirects nested protected paths too", () => {
    const target = redirectTarget(middleware(request("/curriculum/abc-123")));

    expect(target?.pathname).toBe("/login");
    expect(target?.searchParams.get("redirect")).toBe("/curriculum/abc-123");
  });

  it("preserves the query string in the redirect target", () => {
    const target = redirectTarget(
      middleware(request("/dashboard?tab=progress&page=2"))
    );

    expect(target?.searchParams.get("redirect")).toBe(
      "/dashboard?tab=progress&page=2"
    );
  });

  it("treats an empty cookie value as no session", () => {
    const target = redirectTarget(middleware(request("/dashboard", "")));
    expect(target?.pathname).toBe("/login");
  });
});

describe("middleware: bypass hole is closed", () => {
  it("does not allow ?bypass=true through a protected route", () => {
    const target = redirectTarget(middleware(request("/dashboard?bypass=true")));

    expect(target?.pathname).toBe("/login");
  });

  it("does not allow ?bypass=true on /upload either", () => {
    const target = redirectTarget(middleware(request("/upload?bypass=true")));

    expect(target?.pathname).toBe("/login");
  });
});

describe("middleware: authenticated access", () => {
  it.each(PROTECTED)("allows %s with a valid access cookie", (path) => {
    const res = middleware(request(path, jwt(3600)));

    expect(res.headers.get("location")).toBeNull();
  });

  it("rejects an expired access cookie", () => {
    const target = redirectTarget(middleware(request("/dashboard", jwt(-30))));

    expect(target?.pathname).toBe("/login");
    expect(target?.searchParams.get("redirect")).toBe("/dashboard");
  });

  it("allows navigation when only the refresh cookie is still valid", () => {
    // Access tokens live 1h, refresh 7d. An expired access cookie alone must
    // not evict a user who can still transparently refresh.
    const res = middleware(
      request("/dashboard", jwt(-30), jwt(60 * 60 * 24 * 7))
    );

    expect(res.headers.get("location")).toBeNull();
  });

  it("redirects when both cookies are expired", () => {
    const target = redirectTarget(
      middleware(request("/dashboard", jwt(-30), jwt(-30)))
    );

    expect(target?.pathname).toBe("/login");
  });

  it("rejects a malformed access cookie", () => {
    const target = redirectTarget(
      middleware(request("/dashboard", "garbage-value"))
    );

    expect(target?.pathname).toBe("/login");
  });

  it("accepts an opaque token that carries no exp claim", () => {
    const res = middleware(request("/dashboard", jwt(null)));

    expect(res.headers.get("location")).toBeNull();
  });
});

describe("middleware: route boundaries", () => {
  it("does not protect a public path that merely shares a prefix", () => {
    const res = middleware(request("/uploads-guide"));

    expect(res.headers.get("location")).toBeNull();
  });

  it("leaves unrelated public routes alone", () => {
    for (const path of ["/", "/learn", "/forgot-password"]) {
      expect(middleware(request(path)).headers.get("location")).toBeNull();
    }
  });
});

describe("middleware: auth pages", () => {
  it("sends a signed-in user from /login to the dashboard", () => {
    const target = redirectTarget(middleware(request("/login", jwt(3600))));

    expect(target?.pathname).toBe("/dashboard");
  });

  it("keeps /login reachable without a session", () => {
    expect(middleware(request("/login")).headers.get("location")).toBeNull();
  });

  it("keeps /login reachable when the cookie is expired", () => {
    // Otherwise a stale cookie would trap the user in a redirect loop.
    expect(
      middleware(request("/login", jwt(-30))).headers.get("location")
    ).toBeNull();
  });

  it("keeps /signup reachable without a session", () => {
    expect(middleware(request("/signup")).headers.get("location")).toBeNull();
  });
});
