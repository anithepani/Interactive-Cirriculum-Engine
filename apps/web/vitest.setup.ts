/**
 * Test environment shims.
 *
 * jsdom 25 under Node 26 exposes a `window.localStorage` accessor that returns
 * `undefined`, while the backing `_localStorage` store works fine. Anything
 * touching `localStorage` (all of `src/lib/auth.ts`) would otherwise throw.
 * Bind the global to a real Storage instance so tests exercise production code
 * paths rather than a hand-rolled mock.
 */
import { beforeEach } from "vitest";

function createStorage(): Storage {
  const backing = (window as unknown as { _localStorage?: Storage })
    ._localStorage;
  if (backing && typeof backing.getItem === "function") return backing;

  // Minimal spec-compliant fallback if jsdom internals ever change shape.
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    key: (i: number) => Array.from(map.keys())[i] ?? null,
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => void map.set(k, String(v)),
    removeItem: (k: string) => void map.delete(k),
    clear: () => map.clear(),
  } as Storage;
}

const storage = createStorage();

for (const target of [globalThis, window] as unknown as Array<
  Record<string, unknown>
>) {
  Object.defineProperty(target, "localStorage", {
    value: storage,
    writable: true,
    configurable: true,
  });
}

// Each test starts from an empty session.
beforeEach(() => {
  storage.clear();
});
