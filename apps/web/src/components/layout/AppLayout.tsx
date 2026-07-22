"use client";

import Sidebar from "./Sidebar";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, removeTokens, type AuthUser } from "@/lib/auth";
import { useLayoutStore } from "@/lib/store";
import { Bell, Search, Mail, Moon, Sun, LifeBuoy, Flame, Settings, LogOut } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useThemeMode } from "@/components/ThemeProviders";
import { useNotifications } from "@/components/NotificationsProvider";
import { formatRelativeTime } from "@/lib/time";
import CommandPalette from "@/components/CommandPalette";

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
  
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifOpen && bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (profileOpen && profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [notifOpen, profileOpen]);

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 min-h-screen transition-all duration-300">
        {/* Top bar inside the dashboard */}
        <header className="sticky top-0 z-30 flex h-[68px] items-center justify-between border-b border-ink/5 bg-canvas/80 px-6 backdrop-blur-md">
          {/* Search bar placeholder */}
          <button 
            onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
            className="group flex h-11 w-full max-w-md items-center gap-3 rounded-full border border-ink/10 bg-white px-4 shadow-sm transition hover:border-ink/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 dark:bg-zinc-900 dark:border-zinc-800 dark:hover:border-zinc-700"
          >
            <Search className="h-4 w-4 text-ink-soft/60 transition group-hover:text-indigo-500" />
            <span className="flex-1 text-left text-sm text-ink-soft/60 transition group-hover:text-ink-soft">
              Search your course...
            </span>
            <kbd className="hidden items-center gap-1 rounded-md border border-ink/10 bg-ink/5 px-2 py-1 text-[10px] font-semibold text-ink-soft sm:flex dark:border-zinc-800 dark:bg-zinc-800">
              CTRL+K
            </kbd>
          </button>

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
                <span className="material-symbols-outlined text-[20px]">help_center</span>
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

            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen((v) => !v)}
                className="flex items-center gap-3 outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-full pr-1 transition hover:bg-ink/5"
              >
                <span className="hidden text-sm font-semibold text-ink sm:block py-2 pl-3">
                  {user ? user.name : "Loading..."}
                </span>
                
                <div className={`relative h-10 w-10 rounded-full bg-canvas shadow-sm ring-2 ring-offset-2 ${
                  user?.streak_color === 'rose' ? 'ring-rose-500' :
                  user?.streak_color === 'indigo' ? 'ring-indigo-500' :
                  user?.streak_color === 'amber' ? 'ring-amber-500' :
                  user?.streak_color === 'purple' ? 'ring-purple-500' :
                  user?.streak_color === 'cyan' ? 'ring-cyan-500' :
                  user?.streak_color === 'fuchsia' ? 'ring-fuchsia-500' :
                  user?.streak_color === 'orange' ? 'ring-orange-500' :
                  user?.streak_color === 'blue' ? 'ring-blue-500' :
                  'ring-emerald-500'
                }`}>
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="Avatar" className="h-full w-full rounded-full object-cover" />
                  ) : (
                    <div className="bg-indigo-100 text-sm font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 rounded-full h-full w-full flex items-center justify-center">
                      {initials}
                    </div>
                  )}
                  {user?.streak_count !== undefined && user.streak_count > 0 && (
                    <div className={`absolute -bottom-1 -right-1 flex h-4 w-auto min-w-[16px] items-center justify-center gap-0.5 rounded-full border-2 border-white px-1 shadow-sm bg-white ${
                      user?.streak_color === 'rose' ? 'text-rose-500' :
                      user?.streak_color === 'indigo' ? 'text-indigo-500' :
                      user?.streak_color === 'amber' ? 'text-amber-500' :
                      user?.streak_color === 'purple' ? 'text-purple-500' :
                      user?.streak_color === 'cyan' ? 'text-cyan-500' :
                      user?.streak_color === 'fuchsia' ? 'text-fuchsia-500' :
                      user?.streak_color === 'orange' ? 'text-orange-500' :
                      user?.streak_color === 'blue' ? 'text-blue-500' :
                      'text-emerald-500'
                    }`}>
                      <Flame className="h-2 w-2 fill-current" />
                      <span className="text-[8px] font-bold leading-none">{user.streak_count}</span>
                    </div>
                  )}
                </div>
              </button>

              {profileOpen && (
                <div className="absolute right-0 top-14 w-64 overflow-hidden rounded-2xl border border-ink/10 bg-white/80 shadow-xl backdrop-blur-xl dark:bg-zinc-900/90 z-50">
                  <div className="border-b border-ink/5 p-4">
                    <p className="font-semibold text-ink truncate">{user?.name}</p>
                    <p className="text-xs text-ink-soft truncate">{user?.email}</p>
                  </div>
                  <div className="p-2 flex flex-col gap-1">
                    <Link
                      href="/settings"
                      onClick={() => setProfileOpen(false)}
                      className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-ink-soft transition hover:bg-indigo-50 hover:text-indigo-600 dark:hover:bg-indigo-900/30 dark:hover:text-indigo-400"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                    <button
                      onClick={() => {
                        setProfileOpen(false);
                        removeTokens();
                        window.location.href = "/auth/login";
                      }}
                      className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-ink-soft transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400 w-full text-left"
                    >
                      <LogOut className="h-4 w-4" />
                      Log Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="p-8 flex-1">
          {children}
        </main>

        {/* Global App Footer */}
        <footer className="mt-auto border-t border-ink/5 px-8 py-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p className="text-sm text-ink-soft">
              &copy; {new Date().getFullYear()} Interactive Curriculum Engine
            </p>
            <div className="flex items-center gap-6 text-sm font-medium text-ink-soft">
              <Link href="/support" className="transition hover:text-ink">Support</Link>
              <Link href="/settings" className="transition hover:text-ink">Settings</Link>
            </div>
          </div>
        </footer>
      </div>
      <CommandPalette />
    </div>
  );
}
