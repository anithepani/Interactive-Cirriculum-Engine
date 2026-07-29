import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  setTokens,
  removeTokens,
  getToken,
  getRefreshToken,
  authFetch,
  refreshAccessToken,
  safeRedirectPath,
} from "./auth";

const ok = (body: unknown = {}) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
const unauthorized = () => new Response(null, { status: 401 });

let assign: ReturnType<typeof vi.fn>;

beforeEach(() => {
  localStorage.clear();
  // jsdom's window.location.assign is not implemented; replace it so the
  // "bounce to login" path is observable instead of throwing.
  assign = vi.fn();
  Object.defineProperty(window, "location", {
    value: {
      pathname: "/dashboard",
      search: "",
      assign,
    },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("safeRedirectPath", () => {
  it("allows internal absolute paths", () => {
    expect(safeRedirectPath("/upload")).toBe("/upload");
    expect(safeRedirectPath("/curriculum/abc?tab=notes")).toBe(
      "/curriculum/abc?tab=notes"
    );
  });

  it("falls back for empty input", () => {
    expect(safeRedirectPath(null)).toBe("/dashboard");
    expect(safeRedirectPath("")).toBe("/dashboard");
    expect(safeRedirectPath(undefined)).toBe("/dashboard");
  });

  it("rejects absolute external URLs", () => {
    expect(safeRedirectPath("https://evil.test/steal")).toBe("/dashboard");
    expect(safeRedirectPath("http://evil.test")).toBe("/dashboard");
  });

  it("rejects protocol-relative and backslash open-redirect payloads", () => {
    expect(safeRedirectPath("//evil.test")).toBe("/dashboard");
    expect(safeRedirectPath("/\\evil.test")).toBe("/dashboard");
  });

  it("rejects redirects back to auth pages to avoid a loop", () => {
    expect(safeRedirectPath("/login")).toBe("/dashboard");
    expect(safeRedirectPath("/signup")).toBe("/dashboard");
    expect(safeRedirectPath("/auth/callback")).toBe("/dashboard");
  });
});

describe("setTokens", () => {
  it("stores tokens and posts them to the session route", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    const result = await setTokens("access-1", "refresh-1");

    expect(result).toBe(true);
    expect(getToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/auth/session");
    expect((init as RequestInit).method).toBe("POST");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      access_token: "access-1",
      refresh_token: "refresh-1",
    });
  });

  it("reports failure when the session route rejects the token", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(unauthorized());

    // Callers must not navigate on false: middleware would bounce them back.
    await expect(setTokens("access-1", "refresh-1")).resolves.toBe(false);
  });

  it("reports failure when the session request throws", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));

    await expect(setTokens("access-1", "refresh-1")).resolves.toBe(false);
  });
});

describe("removeTokens", () => {
  it("clears storage and asks the server to expire cookies", async () => {
    localStorage.setItem("access_token", "access-1");
    localStorage.setItem("refresh_token", "refresh-1");
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    await removeTokens();

    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith("/auth/session", { method: "DELETE" });
  });

  it("still clears local storage when the server call fails", async () => {
    localStorage.setItem("access_token", "access-1");
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));

    await removeTokens();

    expect(getToken()).toBeNull();
  });
});

describe("authFetch", () => {
  it("attaches the bearer header", async () => {
    localStorage.setItem("access_token", "access-1");
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    await authFetch("/api/v1/auth/me");

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer access-1"
    );
  });

  it("defaults JSON content type for a plain body", async () => {
    localStorage.setItem("access_token", "access-1");
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    await authFetch("/api/v1/thing", { method: "POST", body: "{}" });

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Content-Type")).toBe(
      "application/json"
    );
  });

  it("never overrides the multipart boundary for FormData", async () => {
    localStorage.setItem("access_token", "access-1");
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    await authFetch("/api/v1/upload", {
      method: "POST",
      body: new FormData(),
    });

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Content-Type")).toBeNull();
  });

  it("refreshes once and retries the original request on 401", async () => {
    localStorage.setItem("access_token", "stale");
    localStorage.setItem("refresh_token", "refresh-1");

    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(ok({ access_token: "fresh" }))
      .mockResolvedValueOnce(ok()) // session cookie sync
      .mockResolvedValueOnce(ok({ id: "u1" }));

    const res = await authFetch("/api/v1/auth/me");

    expect(res.status).toBe(200);
    expect(getToken()).toBe("fresh");

    const refreshCalls = fetchSpy.mock.calls.filter(
      ([url]) => url === "/api/v1/auth/refresh"
    );
    expect(refreshCalls).toHaveLength(1);

    // The retry must carry the rotated token, not the stale one.
    const retry = fetchSpy.mock.calls.at(-1)?.[1] as RequestInit;
    expect(new Headers(retry.headers).get("Authorization")).toBe("Bearer fresh");
    expect(assign).not.toHaveBeenCalled();
  });

  it("does not attempt a refresh when no refresh token exists", async () => {
    localStorage.setItem("access_token", "stale");
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(unauthorized());

    await authFetch("/api/v1/auth/me");

    expect(
      fetchSpy.mock.calls.filter(([url]) => url === "/api/v1/auth/refresh")
    ).toHaveLength(0);
  });

  it("clears the session and redirects to login when refresh fails", async () => {
    localStorage.setItem("access_token", "stale");
    localStorage.setItem("refresh_token", "refresh-1");

    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/auth/session") return ok();
      return unauthorized();
    });

    await authFetch("/api/v1/auth/me");

    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(assign).toHaveBeenCalledWith(
      "/login?redirect=%2Fdashboard"
    );
  });

  it("preserves the query string in the login redirect", async () => {
    (window.location as unknown as { search: string }).search = "?tab=notes";
    localStorage.setItem("access_token", "stale");
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/auth/session") return ok();
      return unauthorized();
    });

    await authFetch("/api/v1/auth/me");

    expect(assign).toHaveBeenCalledWith(
      `/login?redirect=${encodeURIComponent("/dashboard?tab=notes")}`
    );
  });

  it("does not redirect when already on an auth page", async () => {
    (window.location as unknown as { pathname: string }).pathname = "/login";
    localStorage.setItem("access_token", "stale");
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/auth/session") return ok();
      return unauthorized();
    });

    await authFetch("/api/v1/auth/me");

    expect(assign).not.toHaveBeenCalled();
  });
});

describe("refreshAccessToken", () => {
  it("shares one in-flight refresh across concurrent callers", async () => {
    localStorage.setItem("refresh_token", "refresh-1");

    let refreshCalls = 0;
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/api/v1/auth/refresh") {
        refreshCalls += 1;
        // Yield so all three callers are queued before this resolves.
        await new Promise((r) => setTimeout(r, 10));
        return ok({ access_token: "fresh" });
      }
      return ok();
    });

    const results = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    expect(refreshCalls).toBe(1);
    expect(results).toEqual(["fresh", "fresh", "fresh"]);
  });

  it("returns null and clears the session on a rejected refresh", async () => {
    localStorage.setItem("access_token", "stale");
    localStorage.setItem("refresh_token", "refresh-1");
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/auth/session") return ok();
      return unauthorized();
    });

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("rejects a malformed refresh body instead of storing undefined", async () => {
    localStorage.setItem("access_token", "stale");
    localStorage.setItem("refresh_token", "refresh-1");
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/api/v1/auth/refresh") return ok({ token_type: "bearer" });
      return ok();
    });

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(getToken()).toBeNull();
  });

  it("returns null without a request when there is no refresh token", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(ok());

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("syncs the session cookie with the rotated access token", async () => {
    localStorage.setItem("refresh_token", "refresh-1");
    const fetchSpy = vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (url === "/api/v1/auth/refresh") return ok({ access_token: "fresh" });
      return ok();
    });

    await refreshAccessToken();

    const sessionCall = fetchSpy.mock.calls.find(
      ([url]) => url === "/auth/session"
    );
    expect(sessionCall).toBeDefined();
    expect(
      JSON.parse((sessionCall?.[1] as RequestInit).body as string)
    ).toEqual({ access_token: "fresh", refresh_token: "refresh-1" });
  });
});
