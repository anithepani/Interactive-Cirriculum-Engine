"use client";

import { usePathname } from "next/navigation";

export default function MainContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAppRoute = /^\/(dashboard|exercises|progress|settings|upload|curriculum|support|discover|curricula|reader)/.test(pathname || "");
  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  const shouldRemovePadding = isAppRoute || isAuthRoute;

  return <main className={`flex-1 ${shouldRemovePadding ? "" : "pt-16"}`}>{children}</main>;
}
