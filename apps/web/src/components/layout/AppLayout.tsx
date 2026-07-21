"use client";

import Sidebar from "./Sidebar";
import { useEffect, useState } from "react";
import { getCurrentUser, type AuthUser } from "@/lib/auth";
import { useLayoutStore } from "@/lib/store";
import { Bell, Search, Mail, Moon, Sun } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useThemeMode } from "@/components/ThemeProviders";

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
              <button className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:text-ink dark:bg-zinc-900">
                <Mail className="h-4 w-4" />
              </button>
              <button className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:text-ink relative dark:bg-zinc-900">
                <Bell className="h-4 w-4" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500"></span>
              </button>
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
