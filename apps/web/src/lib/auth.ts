const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

export interface AuthUser {
  id: number;
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

function setCookie(name: string, value: string, maxAge: number) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; path=/; max-age=0`;
}

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const setTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  setCookie(ACCESS_TOKEN_KEY, accessToken, COOKIE_MAX_AGE);
  setCookie(REFRESH_TOKEN_KEY, refreshToken, COOKIE_MAX_AGE);
};

export const removeTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  deleteCookie(ACCESS_TOKEN_KEY);
  deleteCookie(REFRESH_TOKEN_KEY);
};

export const isAuthenticated = (): boolean => !!getToken();

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      removeTokens();
      return null;
    }
    const data = await res.json();
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    setCookie(ACCESS_TOKEN_KEY, data.access_token, COOKIE_MAX_AGE);
    return data.access_token;
  } catch {
    removeTokens();
    return null;
  }
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
