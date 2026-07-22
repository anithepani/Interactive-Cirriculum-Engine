"use client";

import { usePathname } from "next/navigation";

export default function MainContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // We remove pt-16 on app routes so it doesn't push the AppLayout down
  const isAppRoute = /^\/(dashboard|exercises|progress|settings|upload|curriculum|support|discover|curricula|reader)/.test(pathname || "");

  return <main className={`flex-1 ${isAppRoute ? "" : "pt-16"}`}>{children}</main>;
}
