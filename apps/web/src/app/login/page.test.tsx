import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import LoginPage from "./page";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh }),
}));

// The avatar pulls in heavy animation deps that are irrelevant here.
vi.mock("@/components/InteractiveAvatar", () => ({
  InteractiveAvatar: () => null,
}));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const LOGIN_OK = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  user: { id: "0f8f7a2e-1c3d-4b5a-9e6f-2a1b3c4d5e6f", name: "A", email: "a@b.c" },
};

/** Fill and submit the credential form. */
async function submitLogin() {
  const { fireEvent } = await import("@testing-library/react");

  fireEvent.input(screen.getByPlaceholderText("you@example.com"), {
    target: { value: "a@b.c" },
  });
  fireEvent.input(screen.getByPlaceholderText("••••••••"), {
    target: { value: "hunter2" },
  });
  fireEvent.submit(screen.getByRole("button", { name: /log in/i }).closest("form")!);
}

function setSearch(search: string) {
  Object.defineProperty(window, "location", {
    value: { ...window.location, search, pathname: "/login" },
    writable: true,
    configurable: true,
  });
}

beforeEach(() => {
  setSearch("");
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("LoginPage", () => {
  it("creates the session before navigating to the dashboard", async () => {
    const calls: string[] = [];
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      calls.push(String(url));
      if (String(url) === "/api/v1/auth/login") return json(LOGIN_OK);
      return json({ ok: true });
    });

    render(<LoginPage />);
    await submitLogin();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));

    // Ordering is the whole point of the fix: the middleware-visible cookie
    // must exist before the client-side navigation happens.
    expect(calls).toEqual(["/api/v1/auth/login", "/auth/session"]);
    expect(localStorage.getItem("access_token")).toBe("access-1");
  });

  it("honours a safe internal redirect target", async () => {
    setSearch("?redirect=%2Fupload");
    vi.spyOn(global, "fetch").mockImplementation(async (url) =>
      String(url) === "/api/v1/auth/login" ? json(LOGIN_OK) : json({ ok: true })
    );

    render(<LoginPage />);
    await submitLogin();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/upload"));
  });

  it("refuses an external redirect target", async () => {
    setSearch("?redirect=https%3A%2F%2Fevil.test");
    vi.spyOn(global, "fetch").mockImplementation(async (url) =>
      String(url) === "/api/v1/auth/login" ? json(LOGIN_OK) : json({ ok: true })
    );

    render(<LoginPage />);
    await submitLogin();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows the API error and does not navigate on bad credentials", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      json({ detail: "Invalid credentials" }, 401)
    );

    render(<LoginPage />);
    await submitLogin();

    expect(await screen.findByText("Invalid credentials")).toBeDefined();
    expect(replace).not.toHaveBeenCalled();
  });

  it("does not navigate when the session cookie could not be set", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (String(url) === "/api/v1/auth/login") return json(LOGIN_OK);
      return new Response(null, { status: 401 }); // /auth/session rejected
    });

    render(<LoginPage />);
    await submitLogin();

    // Navigating here is exactly what produced the silent bounce back to /login.
    expect(await screen.findByText(/session could not be started/i)).toBeDefined();
    expect(replace).not.toHaveBeenCalled();
  });
});
