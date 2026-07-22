"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Library,
  Dumbbell,
  LineChart,
  LifeBuoy,
  Settings,
  LogOut,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Compass,
} from "lucide-react";
import { removeTokens } from "@/lib/auth";
import { useLayoutStore } from "@/lib/store";

function HelpCenterIcon(props: any) {
  return (
    <span className={`material-symbols-outlined text-[20px] ${props.className || ''}`}>
      help_center
    </span>
  );
}

const MENU_ITEMS = [
  { label: "Overview", isHeader: true },
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Discover", href: "/discover", icon: Compass },
  { label: "My Curricula", href: "/curricula", icon: Library },
  { label: "Exercises", href: "/exercises", icon: Dumbbell },
  { label: "Progress", href: "/progress", icon: LineChart },
  { label: "Support", href: "/support", icon: HelpCenterIcon },
  { label: "Settings", isHeader: true, className: "mt-6" },
  { label: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    removeTokens();
    router.push("/");
  };

  const { isSidebarCollapsed, toggleSidebar } = useLayoutStore();

  return (
    <aside
      className={`sticky top-0 self-start z-40 hidden h-screen shrink-0 flex-col border-r border-ink/10 bg-white py-8 transition-all duration-300 lg:flex ${
        isSidebarCollapsed ? "w-20" : "w-64"
      }`}
    >
      {/* Collapse Toggle */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-9 flex h-6 w-6 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft shadow-sm hover:text-ink hover:shadow"
      >
        {isSidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {/* Logo */}
      <div className={`mb-10 px-8 ${isSidebarCollapsed ? "px-6" : "px-8"}`}>
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          {!isSidebarCollapsed && (
            <span className="font-display text-xl font-bold tracking-tight text-ink">
              ICE
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className={`flex-1 space-y-1 ${isSidebarCollapsed ? "px-2" : "px-4"}`}>
        {MENU_ITEMS.map((item, idx) => {
          if (item.isHeader) {
            return (
              <div
                key={idx}
                className={`pb-2 pt-4 text-xs font-semibold uppercase tracking-wider text-ink-soft/50 ${
                  isSidebarCollapsed ? "text-center px-0" : "px-4"
                } ${item.className || ""}`}
              >
                {!isSidebarCollapsed ? item.label : "•••"}
              </div>
            );
          }

          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <Link
              key={item.label}
              href={item.href!}
              title={isSidebarCollapsed ? item.label : undefined}
              className={`group flex items-center rounded-xl py-3 text-sm font-medium transition-all ${
                isSidebarCollapsed ? "justify-center px-0" : "gap-3 px-4"
              } ${
                isActive
                  ? "bg-indigo-50 text-indigo-700 font-semibold dark:bg-indigo-950 dark:text-indigo-300"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-zinc-800"
              }`}
            >
              {item.icon && (
                <item.icon
                  className={`h-5 w-5 shrink-0 transition-colors ${
                    isActive ? "text-indigo-700 dark:text-indigo-300" : "text-slate-500 group-hover:text-slate-700 dark:text-slate-400 dark:group-hover:text-slate-200"
                  }`}
                />
              )}
              {!isSidebarCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className={`mt-auto pb-4 ${isSidebarCollapsed ? "px-2" : "px-4"}`}>
        <button
          onClick={handleLogout}
          title={isSidebarCollapsed ? "Logout" : undefined}
          className={`group flex w-full items-center rounded-xl py-3 text-sm font-medium text-rose-500 transition-all hover:bg-rose-50 hover:text-rose-600 ${
            isSidebarCollapsed ? "justify-center px-0" : "gap-3 px-4"
          }`}
        >
          <LogOut className="h-5 w-5 shrink-0 transition-colors text-rose-400 group-hover:text-rose-500" />
          {!isSidebarCollapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}
