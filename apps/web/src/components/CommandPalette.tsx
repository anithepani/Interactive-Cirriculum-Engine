"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Search, MonitorPlay, BookOpen, User, Flame, X, Compass, Plus, Settings } from "lucide-react";
import useSWR from "swr";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary } from "@/lib/types";

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  // Load curricula for search
  const { data: curricula } = useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((open) => !open);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Quick navigation actions
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

  if (!isOpen) return null;

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

        {/* Command Palette Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="relative w-full max-w-2xl overflow-hidden rounded-[2rem] bg-white/80 p-2 shadow-2xl backdrop-blur-xl ring-1 ring-ink/5"
        >
          <div className="flex items-center gap-3 border-b border-ink/10 px-4 py-4">
            <Search className="h-5 w-5 text-ink-soft" />
            <input
              type="text"
              autoFocus
              placeholder="What do you want to learn? (Type a course name or action)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent text-lg font-medium text-ink outline-none placeholder:text-ink-soft/50"
            />
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-full p-2 text-ink-soft transition hover:bg-ink/5 hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="max-h-[60vh] overflow-y-auto px-2 py-4">
            {query && filteredCurricula.length > 0 && (
              <div className="mb-6">
                <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-ink-soft">
                  Curricula
                </p>
                <div className="flex flex-col gap-1">
                  {filteredCurricula.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setIsOpen(false);
                        router.push(`/curriculum/${c.id}`);
                      }}
                      className="group flex items-center gap-4 rounded-xl px-4 py-3 text-left transition hover:bg-indigo-500 hover:text-white focus:bg-indigo-500 focus:text-white"
                    >
                      <MonitorPlay className="h-5 w-5 text-indigo-500 group-hover:text-white group-focus:text-white" />
                      <div className="flex-1">
                        <p className="font-semibold">{c.title}</p>
                        <p className="text-xs text-ink-soft group-hover:text-white/80 group-focus:text-white/80">
                          Status: {c.status}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {filteredActions.length > 0 && (
              <div>
                <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-ink-soft">
                  Quick Actions
                </p>
                <div className="flex flex-col gap-1">
                  {filteredActions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => {
                        setIsOpen(false);
                        router.push(action.href);
                      }}
                      className="group flex items-center gap-4 rounded-xl px-4 py-3 text-left transition hover:bg-ink/5 focus:bg-ink/5"
                    >
                      <action.icon className="h-5 w-5 text-ink-soft group-hover:text-ink group-focus:text-ink" />
                      <span className="font-semibold text-ink">{action.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {query && filteredCurricula.length === 0 && filteredActions.length === 0 && (
              <div className="px-4 py-10 text-center text-ink-soft">
                <p>No results found for &quot;{query}&quot;</p>
              </div>
            )}
          </div>
          
          <div className="border-t border-ink/10 bg-ink/5 px-6 py-3 text-xs text-ink-soft/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>Use</span>
              <kbd className="rounded border border-ink/10 bg-white px-2 py-0.5 shadow-sm">↑</kbd>
              <kbd className="rounded border border-ink/10 bg-white px-2 py-0.5 shadow-sm">↓</kbd>
              <span>to navigate</span>
            </div>
            <div className="flex items-center gap-2">
              <span>to select</span>
              <kbd className="rounded border border-ink/10 bg-white px-2 py-0.5 shadow-sm">Enter</kbd>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
