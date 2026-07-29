import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { POST, DELETE, tokenMaxAge } from "./route";

/** Build an unsigned JWT-shaped token with the given `exp` (seconds). */
function jwt(expSecondsFromNow: number | null): string {
  const claims: Record<string, unknown> = { sub: "user-1" };
  if (expSecondsFromNow !== null) {
    claims.exp = Math.floor(Date.now() / 1000) + expSecondsFromNow;
  }
  const b64 = (o: unknown) =>
    Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(claims)}.sig`;
}

function sessionRequest(body: unknown): NextRequest {
  return new NextRequest("http://localhost:3000/auth/session", {
    method: "POST",
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

/** Parse one Set-Cookie header into name/value/attribute map. */
function parseCookie(header: string) {
  const [pair, ...attrs] = header.split("; ");
  const eq = pair.indexOf("=");
  const flags = new Map<string, string>();
  for (const attr of attrs) {
    const i = attr.indexOf("=");
    if (i === -1) flags.set(attr.toLowerCase(), "");
    else flags.set(attr.slice(0, i).toLowerCase(), attr.slice(i + 1));
  }
  return {
    name: pair.slice(0, eq),
    value: pair.slice(eq + 1),
    flags,
  };
}

function setCookies(res: Response) {
  const all = (res.headers as unknown as { getSetCookie?: () => string[] })
    .getSetCookie?.() ?? [];
  return all.map(parseCookie);
}

beforeEach(() => {
  vi.stubEnv("API_URL", "http://api.test");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("tokenMaxAge", () => {
  it("uses the exp claim when it is sooner than the fallback", () => {
    expect(tokenMaxAge(jwt(120), 3600)).toBeGreaterThan(100);
    expect(tokenMaxAge(jwt(120), 3600)).toBeLessThanOrEqual(120);
  });

  it("caps at the fallback so a long-lived token cannot outlive policy", () => {
    expect(tokenMaxAge(jwt(999999), 3600)).toBe(3600);
  });

  it("returns 0 for an already expired token", () => {
    expect(tokenMaxAge(jwt(-60), 3600)).toBe(0);
  });

  it("falls back for opaque or malformed tokens", () => {
    expect(tokenMaxAge("not-a-jwt", 3600)).toBe(3600);
    expect(tokenMaxAge(jwt(null), 3600)).toBe(3600);
  });
});

describe("POST /auth/session", () => {
  it("rejects a body with no access token", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const res = await POST(sessionRequest({}));

    expect(res.status).toBe(400);
    // No token means we must never even ask the API.
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("rejects invalid JSON", async () => {
    const res = await POST(sessionRequest("{nope"));
    expect(res.status).toBe(400);
  });

  it("does not set a cookie when the API rejects the token", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 401 })
    );

    const res = await POST(sessionRequest({ access_token: jwt(3600) }));

    expect(res.status).toBe(401);
    expect(setCookies(res)).toHaveLength(0);
  });

  it("reports a bad gateway when the API is unreachable", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("ECONNREFUSED"));

    const res = await POST(sessionRequest({ access_token: jwt(3600) }));

    expect(res.status).toBe(502);
    expect(setCookies(res)).toHaveLength(0);
  });

  it("rejects an already expired access token", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 200 })
    );

    const res = await POST(sessionRequest({ access_token: jwt(-10) }));

    expect(res.status).toBe(401);
    expect(setCookies(res)).toHaveLength(0);
  });

  it("validates the token against the API with a bearer header", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));
    const token = jwt(3600);

    await POST(sessionRequest({ access_token: token }));

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/auth/me");
    expect((init as RequestInit & { headers: Record<string, string> }).headers)
      .toMatchObject({ Authorization: `Bearer ${token}` });
  });

  it("sets hardened middleware-visible cookies for a valid token", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 200 })
    );

    const access = jwt(3600);
    const refresh = jwt(60 * 60 * 24 * 7);
    const res = await POST(
      sessionRequest({ access_token: access, refresh_token: refresh })
    );

    expect(res.status).toBe(200);

    const cookies = setCookies(res);
    const accessCookie = cookies.find((c) => c.name === "access_token");
    expect(accessCookie?.value).toBe(access);
    expect(accessCookie?.flags.has("httponly")).toBe(true);
    expect(accessCookie?.flags.has("secure")).toBe(true);
    expect(accessCookie?.flags.get("samesite")?.toLowerCase()).toBe("lax");
    expect(accessCookie?.flags.get("path")).toBe("/");

    const refreshCookie = cookies.find((c) => c.name === "refresh_token");
    expect(refreshCookie?.value).toBe(refresh);
    expect(refreshCookie?.flags.has("httponly")).toBe(true);
  });

  it("omits Secure outside production so local HTTP login still works", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 200 })
    );

    const res = await POST(sessionRequest({ access_token: jwt(3600) }));
    const accessCookie = setCookies(res).find((c) => c.name === "access_token");

    expect(accessCookie?.flags.has("secure")).toBe(false);
    expect(accessCookie?.flags.has("httponly")).toBe(true);
  });

  it("sets only the access cookie when no refresh token is supplied", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 200 })
    );

    const res = await POST(sessionRequest({ access_token: jwt(3600) }));
    const names = setCookies(res).map((c) => c.name);

    expect(names).toContain("access_token");
    expect(names).not.toContain("refresh_token");
  });
});

describe("DELETE /auth/session", () => {
  it("expires both cookies", async () => {
    const res = await DELETE();
    const cookies = setCookies(res);

    for (const name of ["access_token", "refresh_token"]) {
      const cookie = cookies.find((c) => c.name === name);
      expect(cookie, `${name} should be cleared`).toBeDefined();
      expect(cookie?.value).toBe("");
      expect(cookie?.flags.get("max-age")).toBe("0");
    }
  });
});
