"use client";

import Sidebar from "./Sidebar";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, type AuthUser } from "@/lib/auth";
import { useLayoutStore } from "@/lib/store";
import { Bell, Search, Mail, Moon, Sun } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useThemeMode } from "@/components/ThemeProviders";
import { useNotifications } from "@/components/NotificationsProvider";
import { formatRelativeTime } from "@/lib/time";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  const fetchUser = () => {
    getCurrentUser().then(setUser);
  };

  useEffect(() => {
    fetchUser();
    window.addEventListener("userUpdated", fetchUser);
    return () => window.removeEventListener("userUpdated", fetchUser);
  }, []);

  const initials = user?.name
    ? user.name.substring(0, 2).toUpperCase()
    : "U";

  const { isSidebarCollapsed } = useLayoutStore();
  const { mode, toggleColorMode } = useThemeMode();

  const router = useRouter();
  const { notifications, unreadCount, markRead, loading } = useNotifications();
  const [notifOpen, setNotifOpen] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!notifOpen) return;
    const handler = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [notifOpen]);

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? "lg:ml-20" : "lg:ml-64"}`}>
        {/* Top bar inside the dashboard */}
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-ink/5 bg-canvas/80 px-8 backdrop-blur-md">
          {/* Search bar placeholder */}
          <div className="flex h-11 w-full max-w-md items-center gap-3 rounded-full border border-ink/10 bg-white px-4 shadow-sm focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 dark:bg-zinc-900">
            <Search className="h-4 w-4 text-ink-soft/60" />
            <input
              type="text"
              placeholder="Search your course..."
              className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-soft/60"
            />
          </div>

          {/* Right side icons and profile */}
          <div className="flex items-center gap-6">
            <div className="flex gap-3">
              <button
                onClick={toggleColorMode}
                aria-label="Toggle dark mode"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:text-ink dark:bg-zinc-900"
              >
                {mode === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              </button>
              <Link
                href="/support"
                aria-label="Support"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:text-ink dark:bg-zinc-900"
              >
                <Mail className="h-4 w-4" />
              </Link>
              <div className="relative" ref={bellRef}>
                <button
                  onClick={() => setNotifOpen((v) => !v)}
                  aria-label="Notifications"
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:text-ink relative dark:bg-zinc-900"
                >
                  <Bell className="h-4 w-4" />
                  {unreadCount > 0 && (
                    <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500"></span>
                  )}
                </button>
                {notifOpen && (
                  <div className="absolute right-0 top-12 z-50 w-80 overflow-hidden rounded-xl border border-ink/10 bg-white shadow-lg dark:bg-zinc-900">
                    <div className="flex items-center justify-between border-b border-ink/5 px-4 py-3">
                      <span className="text-sm font-semibold text-ink">
                        Notifications
                      </span>
                      {unreadCount > 0 && (
                        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-600 dark:bg-rose-950 dark:text-rose-300">
                          {unreadCount} new
                        </span>
                      )}
                    </div>
                    <div className="max-h-80 overflow-y-auto">
                      {loading ? (
                        <div className="px-4 py-6 text-center text-sm text-ink-soft/60">
                          Loading...
                        </div>
                      ) : notifications.length === 0 ? (
                        <div className="px-4 py-6 text-center text-sm text-ink-soft/60">
                          No notifications
                        </div>
                      ) : (
                        notifications.map((n) => {
                          const unread = (n.read ?? n.is_read) !== true;
                          const curId = n.payload?.curriculum_id;
                          return (
                            <button
                              key={n.id}
                              onClick={() => {
                                if (curId !== undefined) {
                                  router.push(`/curriculum/${curId}`);
                                }
                                markRead(n.id);
                                setNotifOpen(false);
                              }}
                              className={`flex w-full flex-col gap-1 border-b border-ink/5 px-4 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-zinc-800 ${
                                unread
                                  ? "bg-indigo-50/40 dark:bg-indigo-950/20"
                                  : ""
                              }`}
                            >
                              <div className="flex items-start gap-2">
                                {unread && (
                                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indigo-500" />
                                )}
                                <span className="flex-1 text-sm text-ink">
                                  {n.message || n.title || "Notification"}
                                </span>
                              </div>
                              {n.created_at && (
                                <span className="pl-4 text-xs text-ink-soft/60">
                                  {formatRelativeTime(n.created_at)}
                                </span>
                              )}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="hidden text-sm font-semibold text-ink sm:block">
                {user ? user.name : "Loading..."}
              </span>
              <Avatar className="h-10 w-10 border border-ink/10">
                <AvatarFallback className="bg-indigo-100 text-sm font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
