const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

/**
 * Same-origin route that owns the middleware-visible cookies. Cookies are set
 * server-side (HttpOnly) rather than via `document.cookie`, so the edge
 * middleware and the browser can never disagree about whether a session exists.
 */
const SESSION_ENDPOINT = "/auth/session";

export interface AuthUser {
  /** Backend `users.id` is a PostgreSQL UUID, serialized as a string. */
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  xp?: number;
  streak_count?: number;
  streak_color?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  user: AuthUser;
}

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

/**
 * Persist tokens and establish the server-managed session cookie.
 *
 * Callers MUST await this before navigating to a protected route: the cookie is
 * what Next.js middleware reads, so redirecting before it is set is exactly what
 * produced the "logged in but bounced back to /login" loop.
 *
 * Resolves `true` only when the middleware-visible cookie was actually created.
 */
export async function setTokens(
  accessToken: string,
  refreshToken: string
): Promise<boolean> {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);

  try {
    const res = await fetch(SESSION_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        access_token: accessToken,
        refresh_token: refreshToken,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Clear local tokens and expire the server-managed session cookies. */
export async function removeTokens(): Promise<void> {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);

  try {
    await fetch(SESSION_ENDPOINT, { method: "DELETE" });
  } catch {
    // Best-effort: local tokens are already gone, so authFetch cannot succeed.
  }
}

export const isAuthenticated = (): boolean => !!getToken();

/**
 * In-flight refresh, shared across concurrent callers. Several components can
 * hit a 401 at the same moment (dashboard SWR + notifications + SSE token);
 * without this lock each one would independently POST /auth/refresh.
 */
let refreshInFlight: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      await removeTokens();
      return null;
    }

    const data = await res.json().catch(() => null);
    const accessToken = (data as { access_token?: unknown })?.access_token;
    // Guard against a malformed body writing `undefined` into storage.
    if (typeof accessToken !== "string" || accessToken.length === 0) {
      await removeTokens();
      return null;
    }

    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    // Keep the middleware cookie in step with the rotated access token,
    // otherwise navigation would still be gated by the stale value.
    await setTokens(accessToken, refreshToken);
    return accessToken;
  } catch {
    await removeTokens();
    return null;
  }
}

export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

const AUTH_PAGES = ["/login", "/signup", "/logout", "/auth/callback"];

/**
 * Sanitize a `?redirect=` value before navigating to it.
 *
 * Only same-origin, single-slash absolute paths are allowed. This rejects
 * `https://evil.test`, protocol-relative `//evil.test` and backslash variants
 * that some browsers normalize to `//`, so the login form cannot be used as an
 * open redirect. Returns `fallback` for anything unsafe.
 */
export function safeRedirectPath(
  value: string | null | undefined,
  fallback = "/dashboard"
): string {
  if (!value) return fallback;
  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//") || value.startsWith("/\\")) return fallback;
  // Bounce back to an auth page would re-trigger the same navigation loop.
  if (AUTH_PAGES.some((page) => value === page || value.startsWith(`${page}/`))) {
    return fallback;
  }
  return value;
}

/** Send the user to login once, preserving where they were headed. */
function redirectToLogin() {
  if (typeof window === "undefined") return;

  const { pathname, search } = window.location;
  if (AUTH_PAGES.some((page) => pathname.startsWith(page))) return;

  const target = `${pathname}${search}`;
  window.location.assign(`/login?redirect=${encodeURIComponent(target)}`);
}

export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  let token = getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  // Only default to JSON when we have a non-FormData body. For FormData, the
  // browser must set its own multipart/form-data Content-Type (including the
  // boundary), so we never override it here.
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers.has("Content-Type") && options.body && !isFormData) {
    headers.set("Content-Type", "application/json");
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401 && getRefreshToken()) {
    token = await refreshAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
      res = await fetch(url, { ...options, headers });
    }
  }

  // Refresh could not recover the session: clear it and bounce to login once,
  // instead of leaving the page rendered with silent data-fetch failures.
  if (res.status === 401) {
    await removeTokens();
    redirectToLogin();
  }

  return res;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const res = await authFetch("/api/v1/auth/me", { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export const oauthUrl = (provider: "google" | "github") =>
  `${API_BASE}/api/v1/auth/${provider}/authorize`;

/** SWR-compatible fetcher that attaches auth headers. */
export async function authFetcher<T = unknown>(url: string): Promise<T> {
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}
