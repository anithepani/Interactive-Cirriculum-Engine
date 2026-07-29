"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { LogIn, LogOut, Menu, Settings, Sparkles, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { NAV_LINKS } from "@/lib/data";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { getCurrentUser, isAuthenticated, type AuthUser } from "@/lib/auth";

function NavLinkItem({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="group relative px-3 py-2 text-sm font-medium text-ink/80 transition hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:rounded-lg"
    >
      {label}
      <motion.span
        className="absolute bottom-0 left-3 right-3 h-0.5 origin-left scale-x-0 bg-ink"
        whileHover={{ scaleX: 1 }}
        transition={{ duration: 0.2 }}
      />
    </Link>
  );
}

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authed, setAuthed] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  // Hide Navbar on app routes
  const isAppRoute = /^\/(dashboard|exercises|progress|settings|upload|curriculum|support|discover|curricula|reader)/.test(pathname || "");

  useEffect(() => {
    setAuthed(isAuthenticated());
    if (isAuthenticated()) {
      getCurrentUser().then(setUser);
    }
  }, []);

  const handleLogout = () => {
    // The logout page clears tokens and handles the animation
    router.push("/logout");
  };

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "ICE";

  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  if (isAppRoute || isAuthRoute) return null;

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-black/5 bg-white/60 backdrop-blur-lg">
      <div className="mx-auto flex max-w-container items-center justify-between gap-4 px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:rounded-lg"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ink text-lime">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </div>
          <span className="font-display text-lg font-black tracking-tight">ICE</span>
        </Link>

        <nav className="hidden items-center lg:flex" aria-label="Main">
          {NAV_LINKS.map((link) => (
            <NavLinkItem key={link.href} {...link} />
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {authed ? (
            <>
              <Avatar className="hidden h-9 w-9 sm:flex">
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="hidden sm:flex gap-1.5 text-ink/70"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </Button>
            </>
          ) : (
            <>
              <Link href="/login" className="hidden sm:block">
                <Button variant="ghost" size="sm" className="gap-1.5 text-ink/70">
                  <LogIn className="h-4 w-4" />
                  Log in
                </Button>
              </Link>
              <Link href="/signup" className="hidden sm:block">
                <Button variant="default" size="sm" className="gap-1.5">
                  <UserPlus className="h-4 w-4" />
                  Sign up
                </Button>
              </Link>
            </>
          )}

          <motion.button
            type="button"
            className="rounded-full p-2 text-ink/70 hover:bg-ink/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
            whileHover={{ rotate: 90 }}
            transition={{ duration: 0.25 }}
            aria-label="Settings"
          >
            <Settings className="h-5 w-5" />
          </motion.button>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <nav className="mt-8 flex flex-col gap-2" aria-label="Mobile">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "rounded-lg px-3 py-3 text-base font-medium text-ink hover:bg-ink/5",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
                <div className="mt-4 border-t border-ink/10 pt-4 flex flex-col gap-2">
                  {authed ? (
                    <button
                      onClick={() => {
                        handleLogout();
                        setOpen(false);
                      }}
                      className="rounded-lg px-3 py-3 text-base font-medium text-ink hover:bg-ink/5 text-left"
                    >
                      Log out
                    </button>
                  ) : (
                    <>
                      <Link
                        href="/login"
                        onClick={() => setOpen(false)}
                        className="rounded-lg px-3 py-3 text-base font-medium text-ink hover:bg-ink/5"
                      >
                        Log in
                      </Link>
                      <Link
                        href="/signup"
                        onClick={() => setOpen(false)}
                        className="rounded-lg px-3 py-3 text-base font-medium text-indigo-600 hover:bg-indigo-50"
                      >
                        Sign up
                      </Link>
                    </>
                  )}
                </div>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
