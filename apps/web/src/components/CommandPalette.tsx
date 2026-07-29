"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Search, MonitorPlay, BookOpen, Flame, X, Compass, Plus, Settings } from "lucide-react";
import useSWR from "swr";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary } from "@/lib/types";

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();

  const { data: curricula } = useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((open) => !open);
      }
      if (e.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const actions = [
    { id: "dashboard", name: "Dashboard", icon: Compass, href: "/dashboard" },
    { id: "curricula", name: "All Curricula", icon: BookOpen, href: "/curricula" },
    { id: "upload", name: "Upload Video", icon: Plus, href: "/upload" },
    { id: "progress", name: "Progress Report", icon: Flame, href: "/progress" },
    { id: "settings", name: "Settings", icon: Settings, href: "/settings" },
  ];

  const filteredCurricula = (curricula || []).filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase())
  );

  const filteredActions = actions.filter((a) =>
    a.name.toLowerCase().includes(query.toLowerCase())
  );

  // Flat ordered nav list: curricula (when query present) then actions
  const navItems = [
    ...(query && filteredCurricula.length > 0
      ? filteredCurricula.map((c) => ({
          key: c.id,
          run: () => { setIsOpen(false); router.push(`/curriculum/${c.id}`); },
        }))
      : []),
    ...filteredActions.map((a) => ({
      key: a.id,
      run: () => { setIsOpen(false); router.push(a.href); },
    })),
  ];

  // Reset selection when query or list changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query, filteredCurricula.length, filteredActions.length]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, navItems.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        navItems[selectedIndex]?.run();
      }
    },
    [navItems, selectedIndex]
  );

  if (!isOpen) return null;

  // Curricula occupy indices 0..filteredCurricula.length-1 (only when query present)
  const curriculaOffset = query && filteredCurricula.length > 0 ? filteredCurricula.length : 0;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 sm:pt-40">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 bg-ink/40 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="relative w-full max-w-2xl overflow-hidden rounded-[2rem] bg-white/80 dark:bg-zinc-900/90 p-2 shadow-2xl backdrop-blur-xl ring-1 ring-ink/5 dark:ring-white/10"
        >
          {/* Search input row */}
          <div className="flex items-center gap-3 border-b border-ink/10 px-4 py-4">
            <Search className="h-5 w-5 text-ink-soft dark:text-slate-400" />
            <input
              type="text"
              autoFocus
              placeholder="What do you want to learn? (Type a course name or action)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent text-lg font-medium text-ink dark:text-slate-100 outline-none placeholder:text-ink-soft/50 dark:placeholder:text-slate-400"
            />
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-full p-2 text-ink-soft dark:text-slate-400 transition hover:bg-ink/5 dark:hover:bg-white/10 hover:text-ink dark:hover:text-slate-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="max-h-[60vh] overflow-y-auto px-2 py-4">
            {/* Curricula results */}
            {query && filteredCurricula.length > 0 && (
              <div className="mb-6">
                <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-ink-soft dark:text-slate-400">
                  Curricula
                </p>
                <div className="flex flex-col gap-1">
                  {filteredCurricula.map((c, i) => {
                    const active = selectedIndex === i;
                    return (
                      <button
                        key={c.id}
                        onClick={() => { setIsOpen(false); router.push(`/curriculum/${c.id}`); }}
                        onMouseEnter={() => setSelectedIndex(i)}
                        className={`group flex items-center gap-4 rounded-xl px-4 py-3 text-left transition ${
                          active
                            ? "bg-indigo-500 text-white"
                            : "hover:bg-indigo-500 hover:text-white"
                        }`}
                      >
                        <MonitorPlay className={`h-5 w-5 ${active ? "text-white" : "text-indigo-500 group-hover:text-white"}`} />
                        <div className="flex-1">
                          <p className="font-semibold">{c.title}</p>
                          <p className={`text-xs ${active ? "text-white/80" : "text-ink-soft group-hover:text-white/80"}`}>
                            Status: {c.status}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            {filteredActions.length > 0 && (
              <div>
                <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-ink-soft dark:text-slate-400">
                  Quick Actions
                </p>
                <div className="flex flex-col gap-1">
                  {filteredActions.map((action, i) => {
                    const flatIndex = curriculaOffset + i;
                    const active = selectedIndex === flatIndex;
                    return (
                      <button
                        key={action.id}
                        onClick={() => { setIsOpen(false); router.push(action.href); }}
                        onMouseEnter={() => setSelectedIndex(flatIndex)}
                        className={`group flex items-center gap-4 rounded-xl px-4 py-3 text-left transition ${
                          active
                            ? "bg-ink/5 dark:bg-white/10"
                            : "hover:bg-ink/5 dark:hover:bg-white/10"
                        }`}
                      >
                        <action.icon className={`h-5 w-5 ${active ? "text-ink dark:text-slate-100" : "text-ink-soft dark:text-slate-400 group-hover:text-ink dark:group-hover:text-slate-100"}`} />
                        <span className={`font-semibold ${active ? "text-ink dark:text-slate-100" : "text-ink dark:text-slate-200"}`}>
                          {action.name}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {query && filteredCurricula.length === 0 && filteredActions.length === 0 && (
              <div className="px-4 py-10 text-center text-ink-soft dark:text-slate-400">
                <p>No results found for &quot;{query}&quot;</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-ink/10 bg-ink/5 dark:bg-zinc-900/60 px-6 py-3 text-xs text-ink-soft/70 dark:text-slate-400 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>Use</span>
              <kbd className="rounded border border-ink/10 dark:border-zinc-700 bg-white dark:bg-zinc-800 dark:text-zinc-300 px-2 py-0.5 shadow-sm">↑</kbd>
              <kbd className="rounded border border-ink/10 dark:border-zinc-700 bg-white dark:bg-zinc-800 dark:text-zinc-300 px-2 py-0.5 shadow-sm">↓</kbd>
              <span>to navigate</span>
            </div>
            <div className="flex items-center gap-2">
              <span>to select</span>
              <kbd className="rounded border border-ink/10 dark:border-zinc-700 bg-white dark:bg-zinc-800 dark:text-zinc-300 px-2 py-0.5 shadow-sm">Enter</kbd>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
